# Copyright 2019 Dragonchain, Inc.
# Licensed under the Apache License, Version 2.0 (the "Apache License")
# with the following modification; you may not use this file except in
# compliance with the Apache License and the following modification to it:
# Section 6. Trademarks. is deleted and replaced with:
#      6. Trademarks. This License does not grant permission to use the trade
#         names, trademarks, service marks, or product names of the Licensor
#         and its affiliates, except as required to comply with Section 4(c) of
#         the License and to reproduce the content of the NOTICE file.
# You may obtain a copy of the Apache License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the Apache License with the above modification is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the Apache License for the specific
# language governing permissions and limitations under the Apache License.

import json
import os
import base64
import copy
from typing import cast

import requests
import docker

from dragonchain.scheduler import scheduler
from dragonchain.lib.dao import transaction_dao
from dragonchain.lib.dao import transaction_type_dao
from dragonchain.lib.dao import smart_contract_dao
from dragonchain.lib.dto import smart_contract_model
from dragonchain.lib import authorization
from dragonchain.lib import error_reporter
from dragonchain.lib import keys
from dragonchain.lib.interfaces import storage
from dragonchain.lib.interfaces import registry as registry_interface  # Alternate naming to alleviate confusion
from dragonchain.lib import faas
from dragonchain import exceptions
from dragonchain import logger

EVENT = os.environ["EVENT"]
STAGE = os.environ["STAGE"]
FAAS_GATEWAY = os.environ["FAAS_GATEWAY"]
FAAS_REGISTRY = os.environ["FAAS_REGISTRY"]
INTERNAL_ID = os.environ["INTERNAL_ID"]
DRAGONCHAIN_ENDPOINT = os.environ["DRAGONCHAIN_ENDPOINT"]

_log = logger.get_logger()


def main() -> "ContractJob":
    try:
        job = ContractJob(task_definition=json.loads(EVENT))
    except Exception:
        raise exceptions.ContractException("Uncaught error in contract job")

    try:
        if job.update_model is not None:
            job.update()
            change_to_read_user()
            job.model.save()
        elif job.model and job.model.task_type == "create":
            job.create()
            change_to_read_user()
            job.model.save()
        elif job.model and job.model.task_type == "delete":
            job.delete()
    except Exception:
        _log.exception("Uncaught exception raised in contract job")
        if job.update_model is not None:
            job.old_model.status = job.model.status
            job.model = job.old_model
        if job.model.status.get("state") != job.end_error_state:
            # If the exception has not been handled, set state
            job.model.set_state(job.end_error_state, "Unexpected error updating contract")
        change_to_read_user()
        job.model.save()
        raise
    return job


class ContractJob(object):
    """Construct a new ContractJob instance
    Args:
        task_definition (dict): The task that triggered this contract job
    Returns:
        A new ContractJob instance.
    """

    def __init__(self, task_definition: dict):
        # On create, self.model is the creation spec.
        # On delete, self.model is the contract to delete.
        # On update, self.update_model is the update spec, self.model is the contract to update.
        if task_definition["task_type"] == "update":
            self.update_model = smart_contract_model.new_from_build_task(task_definition)
            self.model = cast(smart_contract_model.SmartContractModel, None)  # Set in self.update function
            self.entrypoint = None
            self.end_error_state = smart_contract_model.ContractState.ACTIVE.value
            self.previous_digest = None
        elif task_definition["task_type"] == "create":
            self.update_model = cast(smart_contract_model.SmartContractModel, None)  # Not used in create
            self.model = smart_contract_model.new_from_build_task(task_definition)
            self.function_name = f"contract-{self.model.id}"
            self.faas_image = f"{FAAS_REGISTRY}/customer-contracts:{self.model.id}"
            self.entrypoint = f"{self.model.cmd} {' '.join(self.model.args)}".strip()
            self.end_error_state = smart_contract_model.ContractState.ERROR.value
        elif task_definition["task_type"] == "delete":
            self.update_model = cast(smart_contract_model.SmartContractModel, None)  # Not used in delete
            self.model = smart_contract_model.new_from_build_task(task_definition)
            self.function_name = f"contract-{self.model.id}"
            self.faas_image = f"{FAAS_REGISTRY}/customer-contracts:{self.model.id}"
            self.entrypoint = ""
            self.end_error_state = smart_contract_model.ContractState.DELETE_FAILED.value

    def populate_api_keys(self) -> None:
        key = authorization.register_new_auth_key(smart_contract=True)
        self.model.secrets["secret-key"] = key["key"]
        self.model.secrets["auth-key-id"] = key["id"]
        self.model.auth_key_id = key["id"]

    def populate_env(self) -> None:
        """Populate environment variables for the job"""
        self.model.env["STAGE"] = STAGE
        self.model.env["INTERNAL_ID"] = INTERNAL_ID
        self.model.env["DRAGONCHAIN_ID"] = keys.get_public_id()
        self.model.env["DRAGONCHAIN_ENDPOINT"] = DRAGONCHAIN_ENDPOINT
        self.model.env["SMART_CONTRACT_ID"] = self.model.id
        self.model.env["SMART_CONTRACT_NAME"] = self.model.txn_type

    def create_dockerfile(self) -> str:
        """Creates a new dockerfile with Dragonchain tools built in
        Returns:
            A string path to the folder containing dockerfile.
        """
        _log.info("Creating Dockerfile to build OpenFaaS function")
        current_directory = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(current_directory, "templates", "dockerfile.template")
        dockerfile_path = os.path.join(current_directory, "Dockerfile")

        # Read in template
        with open(template_path) as file:
            template = file.read()

        # Interpolate with base image name
        if self.update_model:
            dockerfile = template.format(customerBaseImage=self.update_model.image)
        else:
            dockerfile = template.format(customerBaseImage=self.model.image)

        # Save as Dockerfile and return context directory
        with open(dockerfile_path, "w") as file:
            file.write(dockerfile)
        return current_directory

    def docker_login_if_necessary(self) -> None:
        """Get authorization to pull docker images"""
        if self.update_model and self.update_model.image:
            auth = self.update_model.auth
            registry = self.update_model.image.split("/")[0]
        else:
            auth = self.model.auth
            registry = self.model.image.split("/")[0]

        if auth is not None:
            try:
                username, password = base64.b64decode(auth.encode("utf-8")).decode("utf-8").split(":")
            except Exception:
                _log.exception("Could not decode user provided auth, discarding.")
                self.model.set_state(self.end_error_state, "Unable to log into docker registry")
                raise exceptions.BadDockerAuth("Unable to log into docker registry")

            try:
                # Assume docker hub first, then try as private registry
                self.docker.login(username, password)
                _log.info("Login success")
                return
            except Exception:
                _log.exception("Could not login to docker hub with auth, attempting private registry...")

            try:
                self.docker.login(username, password, registry=registry)
                _log.info("Login success")
            except Exception:
                _log.exception("Could not login to private registry either.")
                self.model.set_state(self.end_error_state, "Unable to log into docker registry")
                raise exceptions.BadDockerAuth("Unable to log into docker registry")

    def get_openfaas_spec(self) -> dict:
        """Get the specification of the OpenFaaS deployment this job represents.
        Returns:
            A dictionary containing all relevant OpenFaaS information. Does not reveal secrets.
        """
        secret_names = [f"sc-{self.model.id}-{x}" for x in self.model.existing_secrets]
        env = {"read_timeout": "60s", "write_timeout": "60s", "write_debug": "true", "combine_output": "false"}
        env.update(self.model.env)
        image = f"{FAAS_REGISTRY}/customer-contracts@{self.model.image_digest}"
        spec = {
            "service": self.function_name,
            "image": image,
            "envProcess": self.entrypoint,
            "envVars": env,
            "secrets": secret_names,
            "labels": {
                "com.openfaas.scale.min": "1",
                "com.openfaas.scale.max": "20",
                "com.openfaas.scale.factor": "20",
                "com.dragonchain.id": INTERNAL_ID,
                "com.openfaas.fwatchdog.version": "0.18.2",  # Update this as the fwatchdog executable in bin is updates
            },
            "limits": {"cpu": "0.50", "memory": "600M"},
            "requests": {"cpu": "0.25", "memory": "600M"},
        }
        _log.info(f"OpenFaaS spec: {spec}")
        return spec

    def pull_image(self, image_name: str) -> docker.models.images.Image:
        _log.info("Checking size of docker image...")
        image = self.docker.images.pull(image_name)  # TODO: get_registry_data
        if image.attrs["Size"] > 524288000:  # 500MB limit for now
            _log.info("Size too big")
            raise exceptions.ContractImageTooLarge("Docker image too big")
        _log.info("Size OK")
        return image

    def delete_contract_image(self, image_digest: str) -> None:
        _log.info("Deleting contract image")
        try:
            registry_interface.delete_image(repository="customer-contracts", image_digest=image_digest)
        except Exception:
            _log.exception("Error deleting contract image")
            self.model.set_state(state=self.end_error_state, msg="Failing deleting stored image")

    def build_contract_image(self) -> None:
        """Build a smart contract to OpenFaaS"""
        self.docker = docker.from_env()
        self.docker_login_if_necessary()

        if self.update_model:
            self.model.image = self.update_model.image

        _log.info(f"Building OpenFaas image from {self.model.image}")

        try:
            _log.info(f"Pulling {self.model.image} and checking its size")
            self.pull_image(self.model.image)
        except docker.errors.APIError:
            _log.exception("Docker error")
            self.model.set_state(state=self.end_error_state, msg="Docker pull error")
            raise exceptions.BadImageError("Docker pull error")
        except exceptions.ContractImageTooLarge:
            _log.exception("Image too large")
            self.model.set_state(state=self.end_error_state, msg="Docker image exceeds 500MB size limitation")
            raise
        except exceptions.BadImageError:
            _log.exception("Bad image")
            self.model.set_state(state=self.end_error_state, msg="Bad docker image")
            raise

        try:
            dockerfile_path = self.create_dockerfile()
            _log.info(f"Building OpenFaaS image {self.faas_image}")
            self.docker.images.build(path=dockerfile_path, tag=self.faas_image, rm=True, timeout=30)
        except (docker.errors.APIError, docker.errors.BuildError):
            _log.exception("Docker error")
            self.model.set_state(state=self.end_error_state, msg="Docker build error")
            raise exceptions.BadImageError("Docker build error")

        _log.info(f"Pushing to docker registry {self.faas_image}")
        try:
            self.docker.images.push(f"{FAAS_REGISTRY}/customer-contracts", tag=self.model.id, auth_config=registry_interface.get_login())
            image = self.docker.images.get(self.faas_image)
            _log.debug(f"Built image attrs: {image.attrs}")
            self.previous_digest = self.model.image_digest
            self.model.image_digest = image.attrs["RepoDigests"][0].split("@")[-1]
        except docker.errors.APIError:
            _log.exception("Docker error")
            self.model.set_state(state=self.end_error_state, msg="Docker push error")
            raise exceptions.BadImageError("Docker push error")

    def create_openfaas_secrets(self) -> None:
        """Creates secrets for openfaas functions

            Args:
                existing_model (obj, optional): The existing model for this contract if action is update

            Returns:
                None
        """
        existing_secrets = self.model.existing_secrets or []

        if self.update_model:
            new_secrets = self.update_model.secrets
        else:
            new_secrets = self.model.secrets

        for secret, value in new_secrets.items():
            secret_name = f"sc-{self.model.id}-{secret.lower()}"
            requests_method = requests.post if secret not in existing_secrets else requests.put

            _log.info(f"Creating secret: {secret_name} at {FAAS_GATEWAY}")
            response = requests_method(
                f"{FAAS_GATEWAY}/system/secrets", headers={"Authorization": faas.get_faas_auth()}, json={"name": secret_name, "value": value}
            )

            _log.info(f"Response: {response.status_code}")
            _log.info(f"Response Body: {response.text}")

            if response.status_code != 202:
                self.model.set_state(state=self.end_error_state, msg="Error creating contract secrets")
                raise exceptions.ContractException("Error creating contract secret")
            existing_secrets.append(secret.lower())

        self.model.existing_secrets = existing_secrets

    def delete_openfaas_secrets(self) -> None:
        """Deletes secrets for an openfaas function

            Returns:
                None
        """
        _log.info(f"Deleting OpenFaaS secrets: {self.model.existing_secrets}")
        for secret in self.model.existing_secrets:
            secret_name = f"sc-{self.model.id}-{secret.lower()}"
            response = requests.delete(f"{FAAS_GATEWAY}/system/secrets", headers={"Authorization": faas.get_faas_auth()}, json={"name": secret_name})
            if response.status_code != 202:
                self.model.set_state(state=self.end_error_state, msg="Error deleting secrets")
            _log.info(f"Delete secret response: {response.status_code}")

    def deploy_to_openfaas(self) -> None:
        """Deploy this job's smart contract to OpenFaaS and update the faas_spec

            Returns:
                None, or throws exceptions.InternalServerError
        """
        _log.info("Deploying to OpenFaaS cluster")
        spec = self.get_openfaas_spec()
        requests_method = requests.post if self.model.task_type == "create" else requests.put

        response = requests_method(f"{FAAS_GATEWAY}/system/functions", headers={"Authorization": faas.get_faas_auth()}, json=spec)
        _log.info(f"Deployment status: {response.status_code}")
        if response.status_code not in [200, 202]:
            _log.info(f"OpenFaaS deploy failure: {response.status_code}")
            self.model.set_state(state=self.end_error_state, msg="Failed message state")
            raise exceptions.ContractException("Contract function deployment failure")

        _log.info("Saving faas_spec.json to storage")
        if os.environ["STORAGE_TYPE"].lower() == "disk":
            os.setuid(1000)
        storage.put_object_as_json(key=f"SMARTCONTRACT/{self.model.id}/faas_spec.json", value=spec)

    def delete_openfaas_function(self) -> None:
        """Delete this job's smart contract in OpenFaaS and remove the faas_spec

            Returns:
                None, or throws exceptions.InternalServerError
        """
        _log.info("Deleting OpenFaaS function")
        response = requests.delete(
            f"{FAAS_GATEWAY}/system/functions", headers={"Authorization": faas.get_faas_auth()}, json={"functionName": self.function_name}
        )

        _log.info(f"Response Status: {response.status_code}")
        if response.status_code != 202:
            self.model.set_state(state=self.end_error_state, msg="Error deleting contract function")
            _log.info("OpenFaaS delete failure")

    def delete_contract_data(self) -> None:
        """Remove all stored information on this smart contract

            Returns:
                None
        """
        _log.info("Deleting contract data")
        try:
            storage.delete_directory(f"SMARTCONTRACT/{self.model.id}")
            _log.info("Removing index")
            smart_contract_dao.remove_smart_contract_index(self.model.id)
            _log.info("Deleting txn type")
            transaction_type_dao.remove_existing_transaction_type(self.model.txn_type)
            key = f"KEYS/{self.model.auth_key_id}"
            _log.info(f"Deleting HMAC key {key}")
            storage.delete(key)
        except Exception:
            _log.exception("Error deleting contract data")
            self.model.set_state(state=self.end_error_state, msg="Error deleting contract data")

    def schedule_contract(self, action: scheduler.SchedulerActions = scheduler.SchedulerActions.CREATE) -> None:
        try:
            scheduler.schedule_contract_invocation(self.model, action=action)
        except exceptions.TimingEventSchedulerError:
            _log.exception("Error scheduling contract")
            self.model.set_state(state=self.end_error_state, msg="Error scheduling contract execution")
            raise

    def unschedule_contract(self) -> None:
        _log.info("Unscheduling contracts")
        try:
            scheduler.schedule_contract_invocation(self.model, action=scheduler.SchedulerActions.DELETE)
        except exceptions.TimingEventSchedulerError:
            _log.exception("Error unscheduling contract")
            self.model.set_state(state=self.end_error_state, msg="Error unscheduling contract execution")

    def ledger(self) -> None:
        _log.info("Ledgering contract action")
        try:
            transaction_dao.ledger_contract_action(
                cast(str, self.model.task_type if not self.update_model else self.update_model.task_type),  # One of these should always be defined
                cast(str, self.model.txn_type if not self.update_model else self.update_model.txn_type),  # One of these should always be defined
                entrypoint=self.entrypoint or "",
                image_digest=self.model.image_digest or "",
            )
        except Exception:
            _log.exception("Error ledgering contract action")
            self.model.set_state(state=self.end_error_state, msg="Error ledgering contract action")

    def migrate_env(self) -> None:
        if self.update_model.env:
            self.model.env.update(self.update_model.env)
        self.populate_env()  # Override any defaults that the user may have specified

    def create(self) -> None:
        """Creates images for the smart contract this job represents and deploys them to OpenFaaS"""
        schedule_condition = self.model.seconds or self.model.cron

        # Create OpenFaaS function
        self.build_contract_image()
        self.populate_env()
        self.populate_api_keys()
        self.create_openfaas_secrets()
        self.deploy_to_openfaas()

        # Schedule the contract
        if schedule_condition:
            self.schedule_contract()

        # Save and ledger
        self.model.set_state(state=smart_contract_model.ContractState.ACTIVE, msg="Creation success")
        self.ledger()

    def update(self) -> None:
        """Get the current version of the smart contract this job represents and update all data"""
        _log.info("Fetching original contract model")
        self.model = smart_contract_dao.get_contract_by_txn_type(self.update_model.txn_type)
        self.old_model = copy.deepcopy(self.model)
        self.entrypoint = f"{self.update_model.cmd or self.model.cmd} {' '.join(self.update_model.args or self.model.args)}".strip()
        self.function_name = f"contract-{self.model.id}"
        self.faas_image = f"{FAAS_REGISTRY}/customer-contracts:{self.model.id}"
        self.model.task_type = self.update_model.task_type
        self.model.start_state = self.update_model.start_state

        _log.info("Setting up conditions")
        # Misc conditions
        faas_condition = (
            self.update_model.image or self.update_model.secrets or self.update_model.env or self.update_model.cmd or self.update_model.args
        )
        build_condition = self.update_model.image
        new_secrets_condition = self.update_model.secrets
        execution_order_condition = self.update_model.execution_order

        # Schedule conditions
        if self.update_model.disable_schedule:
            schedule_condition = False
            unschedule_condition = True
            self.model.seconds = None
            self.model.cron = None
        else:
            old_schedule_exists = self.model.seconds or self.model.cron
            new_schedule_exists = self.update_model.seconds or self.update_model.cron
            inactive_to_active = self.update_model.desired_state == "active" and self.model.start_state == "inactive"
            inactive_to_active_with_existing_schedule = (inactive_to_active and old_schedule_exists) and not new_schedule_exists
            schedule_condition = new_schedule_exists or inactive_to_active_with_existing_schedule
            unschedule_condition = self.update_model.desired_state == smart_contract_model.ContractState.INACTIVE.value

        _log.info("Beginning update")
        # Update execution order
        if execution_order_condition:
            _log.info("Setting execution order")
            self.model.execution_order = self.update_model.execution_order

        # Update OpenFaaS function
        if faas_condition:
            _log.info("Updating function")
            if new_secrets_condition:
                self.create_openfaas_secrets()
            if build_condition:
                self.build_contract_image()
            self.migrate_env()
            self.deploy_to_openfaas()
            if build_condition:
                self.delete_contract_image(image_digest=cast(str, self.previous_digest))  # This should always be a string if this is being called
            # Save deployment
            self.model.update_faas_fields(update_model=self.update_model)

        # Update scheduler
        if schedule_condition:
            _log.info("Scheduling contract")
            action = scheduler.SchedulerActions.UPDATE if (self.model.cron or self.model.seconds) else scheduler.SchedulerActions.CREATE
            self.model.cron = self.update_model.cron
            self.model.seconds = self.update_model.seconds
            self.schedule_contract(action)

        # If desired state is inactive, unschedule any existing contract schedules
        if unschedule_condition:
            _log.info("Unscheduling contract")
            self.unschedule_contract()

        # If user provided desired state, use that. Otherwise set to start_state
        _log.info("Saving")
        end_state = self.update_model.desired_state or self.model.start_state
        self.model.set_state(state=end_state, msg="Contract update success!")

        self.ledger()

    def delete(self) -> None:
        """Delete the smart contract this job represents and all of its data"""
        if self.model.seconds or self.model.cron:
            self.unschedule_contract()
        self.delete_openfaas_secrets()
        self.delete_openfaas_function()
        self.delete_contract_image(image_digest=self.model.image_digest)
        self.delete_contract_data()
        self.ledger()


def change_to_read_user() -> None:
    # USERSPACE_HACK
    # This hack was put in after much frustration. :|
    # We can't build docker containers in user-space. Only root. This means that we must
    # split the commands within this function between uid 0 (required to build contract
    # containers) and uid 1000 which is what the contracts will later run as. Without
    # swapping uid's here, files would be unreadable by other microservices.
    if os.getuid() == 0:
        os.setuid(1000)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_reporter.report_exception(e, "Uncaught error in contract job!")
        raise

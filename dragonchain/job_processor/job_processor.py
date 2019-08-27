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
import time
from typing import Optional, Dict, cast

import fastjsonschema
import kubernetes

from dragonchain.lib import error_reporter
from dragonchain.lib.dto import schema
from dragonchain.lib.database import redis
from dragonchain import logger

DRAGONCHAIN_VERSION = os.environ["DRAGONCHAIN_VERSION"]
INTERNAL_ID = os.environ["INTERNAL_ID"]
STAGE = os.environ["STAGE"]
REGISTRY = os.environ["REGISTRY"]
IAM_ROLE = os.environ["IAM_ROLE"]
NAMESPACE = os.environ["NAMESPACE"]
DEPLOYMENT_NAME = os.environ["DEPLOYMENT_NAME"]
STORAGE_TYPE = os.environ["STORAGE_TYPE"]
STORAGE_LOCATION = os.environ["STORAGE_LOCATION"]
SECRET_LOCATION = os.environ["SECRET_LOCATION"]

_log = logger.get_logger()
_kube: kubernetes.client.BatchV1Api = cast(kubernetes.client.BatchV1Api, None)  # This will always be defined before starting by being set in start()
_validate_sc_build_task = fastjsonschema.compile(schema.smart_contract_build_task_schema)


def start() -> None:
    """Start the next job in the queue"""
    _log.debug("Connecting to service account")
    kubernetes.config.load_incluster_config()

    _log.debug("Creating kubernetes client")
    global _kube
    _kube = kubernetes.client.BatchV1Api()

    _log.debug("Job processor ready!")
    while True:
        start_task()


def get_image_name() -> str:
    """Get the image name of this version of Dragonchain
    Returns:
        A string path to the image being used in this Dragonchain.
    """
    return f"{REGISTRY}/dragonchain_core:{STAGE}-{DRAGONCHAIN_VERSION}"


def get_job_name(contract_id: str) -> str:
    """Get the name of a kubernetes contract job
    Args:
        contract_id: Id of the contract
    Return:
        A string of the given contract's name.
    """
    return f"contract-{contract_id}"


def get_job_labels(event: dict) -> Dict[str, str]:
    """Get kubernetes labels of the given job
    Args:
        event: An invocation of a smart contract job
    Returns:
        An dictionary with kubernetes job labels for a smart contract
    """
    return {
        "app.kubernetes.io/name": get_job_name(event["id"]),
        "app.kubernetes.io/component": f"{DEPLOYMENT_NAME}-job",
        "app.kubernetes.io/version": DRAGONCHAIN_VERSION,
        "app.kubernetes.io/instance": event["id"],
        "app.kubernetes.io/part-of": DEPLOYMENT_NAME,
        "dragonchainId": INTERNAL_ID,
        "stage": STAGE,
    }


def start_task() -> None:
    task_definition = get_next_task()
    if task_definition:
        job = get_existing_job_status(task_definition)
        if job and job.status.active:
            _log.warning("Throwing away task because job already exists")
            return
        if job and (job.status.succeeded or job.status.failed):
            delete_existing_job(task_definition)
        attempt_job_launch(task_definition)


def get_next_task() -> Optional[dict]:
    """Pop the next task off of the job queue
    Returns:
        The next task. Blocks until a job is found.
    """
    _log.info("Awaiting contract task...")
    pop_result = redis.brpop_sync("mq:contract-task", 0, decode=False)
    if pop_result is None:
        return None
    _, event = pop_result
    _log.debug(f"received task: {event}")
    try:
        event = json.loads(event)
        _validate_sc_build_task(event)
    except Exception:
        _log.exception("Error processing task, skipping")
        return None
    _log.info(f"New task request received: {event}")
    return event


def get_existing_job_status(task: dict) -> Optional[kubernetes.client.V1Job]:
    try:
        return _kube.read_namespaced_job_status(f"contract-{task['id']}", NAMESPACE)
    except kubernetes.client.rest.ApiException as e:
        if e.status == 404:
            _log.info("No existing job found")
            return None
        _log.info("Kubernetes API error")
        raise RuntimeError("Could not get existing job status")


def delete_existing_job(task: dict) -> Optional[kubernetes.client.V1Status]:
    try:
        _log.info("Deleting existing job")
        return _kube.delete_namespaced_job(
            f"contract-{task['id']}", NAMESPACE, body=kubernetes.client.V1DeleteOptions(propagation_policy="Background")
        )
    except kubernetes.client.rest.ApiException as e:
        if e.status == 404:
            _log.info("No existing job found")
            return None
        raise RuntimeError("Could not delete existing job")


def attempt_job_launch(event: dict, retry: int = 0) -> None:
    """Launch kubernetes namespaced job given a smart contract invocation
    Args:
        event: An invocation of a smart contract
        retry: The retry count for recursive invocation (dont specify manually)
    """
    if retry > 5:
        # Re-enqueue?
        _log.error("Could not launch job after 5 attempts.")
        raise RuntimeError("Failure to launch job after 5 attempts")

    _log.info("Launching kubernetes job")
    try:
        volume_mounts = [
            kubernetes.client.V1VolumeMount(name="dockersock", mount_path="/var/run/docker.sock"),
            kubernetes.client.V1VolumeMount(name="faas", mount_path="/etc/openfaas-secret", read_only=True),
            kubernetes.client.V1VolumeMount(name="secrets", mount_path=SECRET_LOCATION[: SECRET_LOCATION.rfind("/")], read_only=True),
        ]
        volumes = [
            kubernetes.client.V1Volume(name="dockersock", host_path=kubernetes.client.V1HostPathVolumeSource(path="/var/run/docker.sock")),
            kubernetes.client.V1Volume(name="faas", secret=kubernetes.client.V1SecretVolumeSource(secret_name="openfaas-auth")),
            kubernetes.client.V1Volume(name="secrets", secret=kubernetes.client.V1SecretVolumeSource(secret_name=f"d-{INTERNAL_ID}-secrets")),
        ]
        if STORAGE_TYPE == "disk":
            volume_mounts.append(kubernetes.client.V1VolumeMount(name="main-storage", mount_path=STORAGE_LOCATION))
            volumes.append(
                kubernetes.client.V1Volume(
                    name="main-storage",
                    persistent_volume_claim=kubernetes.client.V1PersistentVolumeClaimVolumeSource(claim_name=f"{DEPLOYMENT_NAME}-main-storage"),
                )
            )

        resp = _kube.create_namespaced_job(
            namespace=NAMESPACE,
            body=kubernetes.client.V1Job(
                metadata=kubernetes.client.V1ObjectMeta(name=get_job_name(event["id"]), labels=get_job_labels(event)),
                spec=kubernetes.client.V1JobSpec(
                    completions=1,
                    parallelism=1,
                    backoff_limit=1,  # This is not respected in k8s v1.11 (https://github.com/kubernetes/kubernetes/issues/54870)
                    active_deadline_seconds=600,
                    template=kubernetes.client.V1PodTemplateSpec(
                        metadata=kubernetes.client.V1ObjectMeta(annotations={"iam.amazonaws.com/role": IAM_ROLE}, labels=get_job_labels(event)),
                        spec=kubernetes.client.V1PodSpec(
                            containers=[
                                kubernetes.client.V1Container(
                                    name=get_job_name(event["id"]),
                                    image=get_image_name(),
                                    security_context=kubernetes.client.V1SecurityContext(privileged=True),
                                    volume_mounts=volume_mounts,
                                    command=["sh"],
                                    args=["entrypoints/contract_job.sh"],
                                    env=[
                                        kubernetes.client.V1EnvVar(name="EVENT", value=json.dumps(event, separators=(",", ":"))),
                                        kubernetes.client.V1EnvVar(name="SERVICE", value="contract-job"),
                                    ],
                                    env_from=[
                                        kubernetes.client.V1EnvFromSource(
                                            config_map_ref=kubernetes.client.V1ConfigMapEnvSource(name=f"{DEPLOYMENT_NAME}-configmap")
                                        )
                                    ],
                                )
                            ],
                            volumes=volumes,
                            restart_policy="Never",
                        ),
                    ),
                ),
            ),
        )
        _log.info(f"Response from API: {resp}")
    except kubernetes.client.rest.ApiException as e:
        _log.exception(f"Error thrown while starting job. status: {e.status}")
        if e.status == 409:
            retry += 1
            _log.warning(f"Failed to launch! Retry attempt ({retry}/5) in 5 seconds")
            time.sleep(5)
            attempt_job_launch(event, retry=retry)
        raise RuntimeError(f"Error thrown while starting job. status: {e.status}")
    except Exception:
        raise RuntimeError("Unexpected error")


if __name__ == "__main__":
    try:
        start()
    except Exception as e:
        error_reporter.report_exception(e, "Job poller failure.")
        raise

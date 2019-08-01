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

import os
import re
import enum
import uuid
from datetime import datetime
from typing import Union, Mapping, Any, Dict, Optional

from apscheduler.triggers.cron import CronTrigger

from dragonchain.lib.dto import schema
from dragonchain.lib.dto import model
from dragonchain import exceptions
from dragonchain.lib.database import elasticsearch

STAGE = os.environ["STAGE"]


class ContractState(enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    UPDATING = "updating"
    DELETING = "deleting"
    DELETE_FAILED = "delete failed"

    @classmethod
    def is_updatable_state(cls, state):
        return state not in [cls.ACTIVE.value, cls.INACTIVE.value, cls.ERROR.value]


class ContractActions(enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


def new_from_build_task(data: Mapping[str, Any]) -> "SmartContractModel":
    if data.get("version") == "1":
        return SmartContractModel(
            task_type=data["task_type"],
            txn_type=data["txn_type"],
            sc_id=data["id"],
            auth=data["auth"],
            image=data["image"],
            cmd=data["cmd"],
            args=data["args"] or [],
            secrets=data["secrets"] or {},
            existing_secrets=data["existing_secrets"] or [],
            env=data["env"] or {},
            cron=data["cron"],
            seconds=data["seconds"],
            execution_order=data["execution_order"],
            start_state=data["start_state"],
            desired_state=data["desired_state"],
        )
    else:
        raise NotImplementedError(f"Version {data.get('version')} is not supported")


def new_contract_from_user(data: Mapping[str, Any]) -> "SmartContractModel":
    """
    Used in creating new contracts
    Input: SmartContract::L1::Create DTO
    Returns: SmartContractModel object
    """
    if data.get("version") in ["3", "latest"]:
        sc_model = SmartContractModel(
            txn_type=data.get("txn_type"),
            image=data.get("image"),
            sc_id=str(uuid.uuid4()),
            auth=data.get("auth"),
            cmd=data.get("cmd"),
            args=data.get("args"),
            env=data.get("env"),
            secrets=data.get("secrets"),
            seconds=data.get("seconds"),
            cron=data.get("cron"),
            execution_order=data.get("execution_order"),
            status={"state": "Pending", "msg": "Contract creating", "timestamp": str(datetime.utcnow())},
        )
        sc_model.validate_secret_names()
        sc_model.check_env_names()
        sc_model.validate_schedule()
        return sc_model
    else:
        raise NotImplementedError(f"Version {data.get('version')} is not supported")


def new_contract_at_rest(data: Mapping[str, Any]) -> "SmartContractModel":
    """
    Used in querying contracts
    Input: SmartContract::L1::AtRest DTO
    Returns: SmartContractModel object
    """
    if data.get("version") == "1":
        return SmartContractModel(
            txn_type=data.get("txn_type"),
            sc_id=data.get("id"),
            status=data.get("status"),
            image=data.get("image"),
            auth_key_id=data.get("auth_key_id"),
            image_digest=data.get("image_digest"),
            cmd=data.get("cmd"),
            args=data.get("args"),
            existing_secrets=data.get("existing_secrets"),
            env=data.get("env"),
            cron=data.get("cron"),
            seconds=data.get("seconds"),
            execution_order=data.get("execution_order"),
        )
    else:
        raise NotImplementedError(f"Version {data.get('version')} is not supported")


def new_update_contract(data: Mapping[str, Any], existing_contract: "SmartContractModel") -> "SmartContractModel":
    """
    Used in update contract
    Input: SmartContract::L1::Update
    Returns: SmartContractModel object
    """
    if data.get("version") == "3":
        sc_model = SmartContractModel(
            desired_state=data.get("desired_state"),
            sc_id=existing_contract.id,
            txn_type=existing_contract.txn_type,
            auth_key_id=existing_contract.auth_key_id,
            image=data.get("image"),
            auth=data.get("auth"),
            cmd=data.get("cmd"),
            args=data.get("args"),
            env=data.get("env"),
            secrets=data.get("secrets"),
            seconds=data.get("seconds"),
            cron=data.get("cron"),
            execution_order=data.get("execution_order"),
        )
        sc_model.validate_secret_names()
        sc_model.check_env_names()
        sc_model.validate_schedule()
        return sc_model
    else:
        raise NotImplementedError(f"Version {data.get('version')} is not supported")


class SmartContractModel(model.Model):
    """
    SmartContractModel class is an abstracted representation of a smart contract object
    """

    def __init__(
        self,
        txn_type=None,
        task_type: Optional[str] = None,
        sc_id=None,
        status=None,
        start_state=None,
        desired_state=None,
        image=None,
        execution_order=None,
        env=None,
        secrets=None,
        existing_secrets=None,
        auth_key_id=None,
        cmd=None,
        args=None,
        cron=None,
        seconds=None,
        auth=None,
        image_digest=None,
    ):
        """Model Constructor"""
        self.txn_type = txn_type
        self.task_type = task_type
        self.id = sc_id
        self.status = status or {}
        self.start_state = start_state
        self.desired_state = desired_state
        self.image = image
        self.env = env
        self.image_digest = image_digest
        self.existing_secrets = existing_secrets
        self.secrets = secrets
        self.auth_key_id = auth_key_id
        self.seconds = seconds
        self.execution_order = execution_order
        self.cmd = cmd
        self.args = args or []
        self.cron = cron
        self.auth = auth
        # This is a lame hack for elasticsearch to know if this model is a smartcontract model without having to import
        # This should be resolved with active record pattern
        self.is_sc_model = True

    def export_as_invoke_request(self, invoke_transaction: dict) -> Dict[str, Any]:
        """Export as a invoke request DTO"""
        return {"version": "1", "contract_id": self.id, "execution_order": self.execution_order, "transaction": invoke_transaction}

    def export_as_search_index(self) -> Dict[str, Any]:
        """Export as search index DTO"""
        return {
            "dcrn": schema.DCRN.SmartContract_L1_Search_Index.value,
            "version": "1",
            "id": self.id,
            "state": self.status.get("state"),
            "txn_type": self.txn_type,
            "execution_order": self.execution_order,
            "s3_object_folder": "SMARTCONTRACT",
            "s3_object_id": f"{self.id}/metadata.json",
        }

    def export_as_at_rest(self) -> Dict[str, Any]:
        """Export as at rest DTO"""
        return {
            "dcrn": schema.DCRN.SmartContract_L1_At_Rest.value,
            "version": "1",
            "txn_type": self.txn_type,
            "id": self.id,
            "status": self.status,
            "image": self.image,
            "auth_key_id": self.auth_key_id,
            "image_digest": self.image_digest,
            "cmd": self.cmd,
            "args": self.args,
            "env": self.env,
            "existing_secrets": self.existing_secrets,
            "cron": self.cron,
            "seconds": self.seconds,
            "execution_order": self.execution_order,
        }

    def export_as_contract_task(self, task_type: ContractActions) -> Dict[str, Any]:
        """Export as build task"""
        return {
            "version": "1",
            "task_type": task_type.value,
            "txn_type": self.txn_type,
            "id": self.id,
            "auth": self.auth,
            "image": self.image,
            "cmd": self.cmd,
            "args": self.args,
            "secrets": self.secrets,
            "existing_secrets": self.existing_secrets,
            "image_digest": self.image_digest,
            "env": self.env,
            "cron": self.cron,
            "seconds": self.seconds,
            "execution_order": self.execution_order,
            "start_state": self.start_state,
            "desired_state": self.desired_state,
        }

    def validate_schedule(self) -> None:
        if self.cron and self.seconds:
            raise exceptions.ValidationException("can only have one of 'seconds' or 'cron'")
        if self.cron:
            try:
                CronTrigger.from_crontab(self.cron)
            except ValueError:
                raise exceptions.ValidationException("The provided cron string is invalid")

    def validate_secret_names(self) -> None:
        if self.secrets is None:
            return
        regex = "[a-zA-Z][a-zA-Z0-9-]{0,16}"
        pattern = re.compile(regex)
        for secret in self.secrets:
            if not pattern.fullmatch(secret):
                raise exceptions.ValidationException(f"secret names must match regex {regex}")

    def check_env_names(self) -> None:
        if self.env is None:
            return

        for key in self.env:
            self.env[key] = str(self.env[key])
        regex = "[a-zA-Z][a-zA-Z0-9._-]+"
        pattern = re.compile(regex)
        for env_var in self.env:
            if not pattern.fullmatch(env_var):
                raise exceptions.ValidationException(f"env names must match regex {regex}")

    def set_state(self, state: Union[str, ContractState], msg: str = "") -> None:
        if not isinstance(msg, str):
            raise TypeError("[SmartContractModel set_state] msg must be type str")
        self.status = {"state": state if isinstance(state, str) else state.value, "msg": msg, "timestamp": str(datetime.utcnow())}

    def update_faas_fields(self, update_model: "SmartContractModel") -> None:
        """Update the fields relating to OpenFaaS function updates"""
        if update_model.image:
            self.image = update_model.image
        if update_model.cmd:
            self.cmd = update_model.cmd
        if update_model.args:
            self.args = update_model.args
        if update_model.env:
            self.env = update_model.env
        if update_model.existing_secrets:
            self.existing_secrets = update_model.existing_secrets

    def save(self) -> None:
        elasticsearch.put_index_in_storage("SMARTCONTRACT", self.id, self)

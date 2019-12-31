# Copyright 2020 Dragonchain, Inc.
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
import enum
from datetime import datetime
from typing import Union, Any, TYPE_CHECKING

from dragonchain.scheduler import timing_event
from dragonchain.lib.database import redis
from dragonchain.scheduler import background_scheduler
from dragonchain import exceptions
from dragonchain import logger

if TYPE_CHECKING:
    from dragonchain.lib.dto import smart_contract_model

_log = logger.get_logger()


class SchedulerActions(enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


def parse_json_or_fail(json_str: Union[str, bytes]) -> Any:
    """
    Common method for parsing json, and failing if malformed.
    """
    try:
        return json.loads(json_str)
    except json.decoder.JSONDecodeError:
        raise exceptions.TimingEventSchedulerError("MALFORMED_JSON")


def subscribe(redis_key: str) -> None:
    pop_result = redis.brpop_sync(redis_key, 0, decode=False)
    if pop_result is None:
        return
    _, string_change_request = pop_result
    redis.delete_sync(f"{redis_key}:errors")
    _log.debug(f"New message: {string_change_request}")
    try:
        change_request = parse_json_or_fail(string_change_request)
        worker(change_request)
        _log.debug(f"Total running jobs: {len(background_scheduler.background_scheduler.get_jobs())}")
    except exceptions.TimingEventSchedulerError as e:
        redis.lpush_sync(
            f"{redis_key}:errors",
            json.dumps({"timestamp": str(datetime.utcnow()), "error": str(e), "command": str(string_change_request)}, separators=(",", ":")),
        )
        _log.exception("FailureByDesign")
        raise


def revive_dead_workers() -> None:
    """
    Revive any dead jobs still in redis
    """
    orphaned_jobs = redis.hgetall_sync("scheduler:params", decode=False)
    for _, string_change_request in orphaned_jobs.items():
        _log.debug(f"Starting orphan job: {string_change_request}")
        params = parse_json_or_fail(string_change_request)
        params["action"] = "create"
        redis.lpush_sync("mq:scheduler", json.dumps(params, separators=(",", ":")))


def schedule_contract_invocation(
    contract_model: "smart_contract_model.SmartContractModel", action: SchedulerActions = SchedulerActions.CREATE
) -> None:
    """Schedule cron smart contracts.
       Call this method only after confirming sc_type is 'cron'
    Args:
        contract_model: a smart contract model which is type cron
    Raises:
        exceptions.TimingEventSchedulerError: when contract model is in a bad state
    """
    if (action.value != "delete") and (contract_model.cron is None and contract_model.seconds is None):
        raise exceptions.TimingEventSchedulerError("You must provide cron or seconds to schedule a job")
    redis.lpush_sync(
        "mq:scheduler",
        json.dumps(
            {
                "action": action.value,
                "contract_id": contract_model.id,
                "txn_type": contract_model.txn_type,
                "execution_order": contract_model.execution_order,
                "cron": contract_model.cron,
                "seconds": contract_model.seconds,
            },
            separators=(",", ":"),
        ),
    )


def worker(change_request: dict) -> None:
    """Process incoming change requests
    Args:
        change_request: dict<ChangeRequest> {contract_id: string, action: SchedulerActions enum, seconds?:int, cron?: string}
    """
    _log.debug(f"Change Request: {change_request}")
    contract_id = change_request["contract_id"]
    action = change_request["action"]
    seconds = change_request.get("seconds")
    cron = change_request.get("cron")
    txn_type = change_request["txn_type"]
    execution_order = change_request["execution_order"]

    # Delete jobs
    if action == "delete" and timing_event.exists(contract_id):
        timing_event.get_by_id(contract_id).delete()

    #  Update job
    if action == "update":
        if not timing_event.exists(contract_id):
            raise exceptions.TimingEventSchedulerError("NOT_FOUND")
        event = timing_event.get_by_id(contract_id)
        event.update(cron=cron, seconds=seconds, execution_order=execution_order, txn_type=txn_type)

    # Create new job
    if action == "create":
        event = timing_event.TimingEvent(cron=cron, seconds=seconds, timing_id=contract_id, execution_order=execution_order, txn_type=txn_type)
        event.start()

    _log.debug(f"Successful {action} on job '{contract_id}'")

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
import time
from typing import Optional, Union

from apscheduler.jobstores.base import ConflictingIdError
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from dragonchain.lib import queue
from dragonchain import logger
from dragonchain.lib import keys
from dragonchain import exceptions
from dragonchain.scheduler import background_scheduler
from dragonchain.lib.database import redis
from dragonchain.lib.dto import smart_contract_model
from dragonchain.lib.dto import transaction_model

JOB_PARAMS_KEY = "scheduler:params"

_log = logger.get_logger()


def exists(timing_id: str) -> bool:
    """Check if a timing event exists by ID
    Args:
        timing_id: The id of a running timing event. Usually a contract_id
    Returns:
        boolean whether a timing event with the specified ID exists
    """
    return redis.hexists_sync(JOB_PARAMS_KEY, timing_id)


def get_by_id(timing_id: str) -> "TimingEvent":
    """Return a TimingEvent instance located by ID.
    Args:
        timing_id: The id of a running timing event. Usually a contract_id
    Returns:
        Instantiated timingEvent instance if found
    Raises:
        exceptions.TimingEventSchedulerError if event is not found
    """
    result = redis.hget_sync(JOB_PARAMS_KEY, timing_id, decode=False)
    if not result:
        raise exceptions.TimingEventSchedulerError("NOT_FOUND")
    params = json.loads(result)
    return TimingEvent(timing_id=params["contract_id"], seconds=params.get("seconds"), cron=params.get("cron"))


class TimingEvent(object):
    """
    TimingEvent
    This class is models of the state transfer Cron/Interval timing events in the Dragonchain system.
    """

    def __init__(
        self, timing_id: str, cron: Optional[str] = "* * * * *", seconds: Optional[int] = None, txn_type: str = None, execution_order: str = None
    ):
        self.cron = cron
        self.id = timing_id
        self.seconds = seconds
        self.execution_order = execution_order
        self.txn_type = txn_type

    def delete(self) -> None:
        """Delete this event"""
        background_scheduler.background_scheduler.remove_job(self.id)
        redis.hdel_sync(JOB_PARAMS_KEY, self.id)

    def update(
        self, txn_type: Optional[str] = None, execution_order: Optional[str] = None, cron: Optional[str] = None, seconds: Optional[int] = None
    ) -> None:
        """Update this event instance
        Args:
            cron: cron expression string ex: "* * * * *"
            seconds: integer of seconds between events. ex: 60
            txn_type: updated transaction type to assign to this instance
            execution_order: "serial" or "parallel
        Raises:
            exceptions.TimingEventSchedulerError<BAD_REQUEST> if no provided update parameters
        """
        if (not cron and not seconds) or (cron and seconds) or not execution_order or not txn_type:
            raise exceptions.TimingEventSchedulerError("BAD_REQUEST")
        if cron:
            self.cron = cron
            self.seconds = None
        elif seconds:
            self.seconds = seconds
            self.cron = None
        if txn_type:
            self.txn_type = txn_type
        if execution_order:
            self.execution_order = execution_order
        self.save()
        background_scheduler.background_scheduler.reschedule_job(self.id, trigger=self.get_trigger())

    def save(self) -> None:
        """Save this event's state to redis"""
        _log.debug("Saving job params.")
        redis.hset_sync(JOB_PARAMS_KEY, self.id, self.as_json())

    def start(self) -> None:
        """Start this timing event's scheduler.
        Raises:
            exceptions.TimingEventSchedulerError<CONFLICT>: when a job with this ID already exists.
        """
        self.save()
        _log.debug("Job params successfully saved.")
        try:
            background_scheduler.background_scheduler.add_job(self.submit_invocation_request, max_instances=1, trigger=self.get_trigger(), id=self.id)
        except ConflictingIdError:
            raise exceptions.TimingEventSchedulerError("CONFLICT")

    def submit_invocation_request(self) -> None:
        """Submit this model as an invocation request to the queue to be handled by the contract invoker"""
        contract_model = smart_contract_model.SmartContractModel(txn_type=self.txn_type, sc_id=self.id, execution_order=self.execution_order)
        txn_model = transaction_model.TransactionModel(
            txn_type=self.txn_type, dc_id=keys.get_public_id(), txn_id="cron", timestamp=str(int(time.time())), payload={}
        )
        invoke_request = contract_model.export_as_invoke_request(invoke_transaction=txn_model.export_as_queue_task(dict_payload=True))

        _log.info(f"Sending invocation request for txn_type: {self.txn_type} contract_id: {self.id}")
        queue.enqueue_generic(content=invoke_request, queue=queue.CONTRACT_INVOKE_MQ_KEY, deadline=0)

    def get_trigger(self) -> Union[IntervalTrigger, CronTrigger]:
        """Get the relevant apscheduler trigger for this timing event"""
        return IntervalTrigger(seconds=self.seconds) if self.seconds else CronTrigger.from_crontab(self.cron)

    def as_json(self) -> str:
        """Returns this instance as serialized create params
        Returns:
            Stringified json representation of this event
        """
        return json.dumps(
            {"cron": self.cron, "seconds": self.seconds, "contract_id": self.id, "execution_order": self.execution_order, "txn_type": self.txn_type},
            separators=(",", ":"),
        )

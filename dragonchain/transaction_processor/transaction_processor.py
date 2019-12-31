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

import os
from typing import Dict, Tuple, Any, TYPE_CHECKING

import apscheduler.events
import apscheduler.triggers.cron
import apscheduler.schedulers.blocking

from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib import error_reporter

if TYPE_CHECKING:
    import apscheduler.events

LEVEL = os.environ["LEVEL"]

_log = logger.get_logger()

_scheduler = apscheduler.schedulers.blocking.BlockingScheduler()


def setup() -> Tuple[Dict[str, str], Any]:
    cron_trigger = {"second": "*/1"}
    if LEVEL == "1":
        cron_trigger = {"second": "*/5"}
        from dragonchain.transaction_processor import level_1_actions as processor
    elif LEVEL == "2":
        from dragonchain.transaction_processor import level_2_actions as processor
    elif LEVEL == "3":
        from dragonchain.transaction_processor import level_3_actions as processor
    elif LEVEL == "4":
        from dragonchain.transaction_processor import level_4_actions as processor
    elif LEVEL == "5":
        cron_trigger = {"minute": "*/1"}
        from dragonchain.transaction_processor import level_5_actions as processor

        processor.setup()  # L5 processor requires setup to be called to configure module state before running
    else:
        raise exceptions.InvalidNodeLevel("Invalid node level")

    return cron_trigger, processor


def error_handler(event: "apscheduler.events.JobExecutionEvent") -> bool:
    exception = event.exception
    message = error_reporter.get_exception_message(exception)
    error_reporter.report_exception(exception, message)
    _scheduler.shutdown()
    return False


if __name__ == "__main__":
    try:
        cron_trigger, processor = setup()
        _scheduler.add_listener(error_handler, apscheduler.events.EVENT_JOB_ERROR)
        _scheduler.add_job(func=processor.execute, trigger=apscheduler.triggers.cron.CronTrigger(**cron_trigger))
        _scheduler.start()
    except Exception as e:
        error_reporter.report_exception(e, "Uncaught transaction processor scheduler error")
        raise

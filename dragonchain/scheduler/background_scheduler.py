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

import apscheduler.schedulers.background
import apscheduler.events

from dragonchain.lib import error_reporter

background_scheduler = apscheduler.schedulers.background.BackgroundScheduler()


def error_handler(event: "apscheduler.events.JobExecutionEvent") -> bool:
    exception = event.exception
    message = error_reporter.get_exception_message(exception)
    error_reporter.report_exception(exception, message)
    background_scheduler.shutdown()
    return False


background_scheduler.add_listener(error_handler, apscheduler.events.EVENT_JOB_ERROR)
background_scheduler.start()

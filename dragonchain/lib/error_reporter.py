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
import json
import time
import traceback

from dragonchain import logger
from dragonchain.lib.dto import schema


_log = logger.get_logger()

REPORT_ERRORS = False

_reporting_type = (os.environ.get("ERROR_REPORTING_TYPE") or "").lower()
if _reporting_type == "sns":
    REPORT_ERRORS = True
    from dragonchain.lib.interfaces.aws.sns import send_error_message as reporter
elif _reporting_type == "storage":
    REPORT_ERRORS = True
    from dragonchain.lib.interfaces.storage import save_error_message as reporter  # noqa: T484 alternative import is expected


def get_exception_message(exception: Exception) -> str:
    if len(exception.args) > 0:
        return str(exception.args[0])
    return ""


def report_exception(exception: Exception, message: str) -> None:
    _log.exception("Error:")
    if REPORT_ERRORS:
        reporter(
            json.dumps(
                {
                    "dcrn": schema.DCRN.Error_InTransit_Template.value.format(os.environ["LEVEL"]),
                    "version": "1",
                    "app": "Dragonchain",
                    "timestamp": int(time.time()),
                    "service": os.environ.get("SERVICE"),
                    "stack_trace": "".join(traceback.format_tb(exception.__traceback__)),
                    "message": json.dumps({"internal_id": os.environ.get("INTERNAL_ID")}),
                },
                separators=(",", ":"),
            )
        )

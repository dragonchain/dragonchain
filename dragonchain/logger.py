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

import logging
import os

SERVICE = os.environ.get("SERVICE") or "temp"
LOG_LEVEL = os.environ.get("LOG_LEVEL")


def get_logger(log_name: str = SERVICE) -> logging.Logger:
    """Get logger for the various processes"""
    log = logging.getLogger(log_name)
    if not log.handlers:
        log.addHandler(logging.StreamHandler())
    # Only 3 level of logging are supported right now (defaults to info level)
    if LOG_LEVEL == "DEBUG":
        log.setLevel(logging.DEBUG)
    elif LOG_LEVEL == "OFF":
        log.disabled = True
    else:
        # default to info level logging
        log.setLevel(logging.INFO)
    return log

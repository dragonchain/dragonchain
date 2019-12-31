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
import base64
import json
from typing import List, Dict, Optional, cast, Any

import requests

from dragonchain import exceptions

FAAS_GATEWAY = os.environ.get("FAAS_LOGS_GATEWAY") or os.environ["FAAS_GATEWAY"]


def get_faas_auth() -> str:
    """Gets authorization to use OpenFaaS

    Returns:
        A string containing authorization for OpenFaaS.
        Returns empty string if authorization is not found, in the case of managed services
    """
    try:
        with open("/etc/openfaas-secret/user", "r") as file:
            username = file.read()
        with open("/etc/openfaas-secret/password", "r") as file:
            password = file.read()
    except FileNotFoundError:
        return ""

    return f"Basic {base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('ascii')}"


def _get_raw_logs(contract_id: str, since: Optional[str] = None, tail: Optional[int] = 100) -> List[str]:
    """Calls openfaas /system/logs endpoint with query parameters for a specific contract

    Returns:
        A list of log JSON strings
    """
    query_params = cast(Dict[str, Any], {"name": f"contract-{contract_id}", "tail": tail or 100, "since": since})
    response = requests.get(f"{FAAS_GATEWAY}/system/logs", params=query_params, headers={"Authorization": get_faas_auth()})
    if response.status_code != 200:
        raise exceptions.OpenFaasException("Error getting contract logs, non-2XX response from OpenFaaS gateway")

    return response.text.split("\n")


def get_logs(contract_id: str, since: Optional[str] = None, tail: Optional[int] = 100) -> List[Dict[str, str]]:
    """Gets the raw logs from openfaas and parses the ndjson into a list of dictionaries

    Returns:
        A list of log dictionaries
    """
    return [json.loads(log) for log in _get_raw_logs(contract_id, since, tail) if log != ""]

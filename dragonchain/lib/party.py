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

import requests

from dragonchain import logger

STAGE = os.environ["STAGE"]
REQUEST_TIMEOUT = 30
PARTY_URL = "https://party.api.dragonchain.com" if STAGE == "prod" else "https://party-staging.api.dragonchain.com"


_log = logger.get_logger()


def get_address_ddss(address: str) -> str:
    """Return the DDSS for a particular address from party api
    Args:
        address: address to fetch ddss for
    Returns:
        Floating point number representing address DDSS
    """
    response = make_party_request("GET", f"/v1/wallet/{address}")
    _log.debug(f"Party response code: {response.status_code}")

    if response.status_code == 200:
        json_response = response.json()
        _log.debug(f"Party response body: {json_response}")
        return str(json_response["adjustedScore"])

    raise RuntimeError("Invalid response from party service")


def make_party_request(http_verb: str, path: str, json_content: dict = None) -> requests.Response:
    if json_content is None:
        json_content = {}
    http_verb = http_verb.upper()
    _log.info(f"[PARTY] Performing {http_verb} request to {path} with data: {json_content}")

    data = json.dumps(json_content, separators=(",", ":")).encode("utf-8") if json_content else b""
    headers = {"Content-Type": "application/json"} if json_content else {}

    return requests.request(method=http_verb, url=f"{PARTY_URL}{path}", headers=headers, data=data, timeout=REQUEST_TIMEOUT)

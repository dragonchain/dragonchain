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

from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib.dto import smart_contract_model
from dragonchain.lib.interfaces import storage
from dragonchain.lib.database import elasticsearch

#  Constants
FOLDER = "SMARTCONTRACT"

_log = logger.get_logger()


def get_contract_by_txn_type(txn_type: str) -> "smart_contract_model.SmartContractModel":
    """Searches for a contract by txn_type"""
    results = elasticsearch.search(folder=FOLDER, query={"query": {"match_phrase": {"txn_type": txn_type}}})["results"]

    if len(results) > 0:
        return smart_contract_model.new_contract_at_rest(results[0])

    raise exceptions.NotFound(f"Smart contract {txn_type} could not be found.")


def get_serial_contracts() -> list:
    """Searches for serial contracts"""
    results = elasticsearch.search(folder=FOLDER, query={"query": {"match_phrase": {"execution_order": "serial"}}})["results"]

    if results:
        return results

    raise exceptions.NotFound("No serial smart contracts found.")


def get_contract_by_id(contract_id: str) -> "smart_contract_model.SmartContractModel":
    """Searches for a contract by contract_id"""
    return smart_contract_model.new_contract_at_rest(storage.get_json_from_object(f"{FOLDER}/{contract_id}/metadata.json"))

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

from typing import List

from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib.dto import smart_contract_model
from dragonchain.lib.interfaces import storage
from dragonchain.lib.database import redisearch

#  Constants
FOLDER = "SMARTCONTRACT"

_log = logger.get_logger()


def get_contract_id_by_txn_type(txn_type: str) -> str:
    results = redisearch.search(
        index=redisearch.Indexes.smartcontract.value, query_str=f"@sc_name:{{{redisearch.get_escaped_redisearch_string(txn_type)}}}", only_id=True
    ).docs
    if results:
        return results[0].id
    raise exceptions.NotFound(f"Smart contract {txn_type} could not be found.")


def get_contract_by_txn_type(txn_type: str) -> smart_contract_model.SmartContractModel:
    """Searches for a contract by txn_type"""
    return smart_contract_model.new_from_at_rest(storage.get_json_from_object(f"{FOLDER}/{get_contract_id_by_txn_type(txn_type)}/metadata.json"))


def list_all_contract_ids() -> List[str]:
    query_result = redisearch.search(index=redisearch.Indexes.smartcontract.value, query_str="*", limit=10000, only_id=True)
    contract_ids = []
    for index in query_result.docs:
        contract_ids.append(index.id)
    return contract_ids


def get_serial_contracts() -> List[smart_contract_model.SmartContractModel]:
    """
    Searches for serial contracts
    Please note this function fetches all smart contract metadata from storage each time it is run, so should be used sparingly
    """
    serial_contracts = []
    for sc_id in list_all_contract_ids():
        sc_model = get_contract_by_id(sc_id)
        if sc_model.execution_order == "serial":
            serial_contracts.append(sc_model)
    return serial_contracts


def add_smart_contract_index(contract: smart_contract_model.SmartContractModel) -> None:
    """Add the index for a smart contract"""
    redisearch.put_document(redisearch.Indexes.smartcontract.value, contract.id, {"sc_name": contract.txn_type}, upsert=True)


def remove_smart_contract_index(contract_id: str) -> None:
    """Remove the index for a smart contract"""
    redisearch.delete_document(redisearch.Indexes.smartcontract.value, contract_id)


def get_contract_by_id(contract_id: str) -> smart_contract_model.SmartContractModel:
    """Searches for a contract by contract_id"""
    return smart_contract_model.new_from_at_rest(storage.get_json_from_object(f"{FOLDER}/{contract_id}/metadata.json"))


def contract_does_exist(contract_id: str) -> bool:
    """Checks if a contract exists or not"""
    return storage.does_object_exist(f"{FOLDER}/{contract_id}/metadata.json")

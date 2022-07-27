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

from typing import List, Optional, Dict

from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib.dto import smart_contract_model
from dragonchain.lib.interfaces import storage
from dragonchain.lib.database import elasticsearch
from dragonchain.lib import faas

#  Constants
FOLDER = "SMARTCONTRACT"

_log = logger.get_logger()


def get_contract_id_by_txn_type(txn_type: str) -> str:
    results = elasticsearch.search(
        index=elasticsearch.Indexes.smartcontract.value,
        query={"query": {"match": {"sc_name": txn_type}}},
    )
    if results:
        return results["results"][0].id
    raise exceptions.NotFound(f"Smart contract {txn_type} could not be found.")


def get_contract_by_txn_type(txn_type: str) -> smart_contract_model.SmartContractModel:
    """Searches for a contract by txn_type"""
    return smart_contract_model.new_from_at_rest(storage.get_json_from_object(f"{FOLDER}/{get_contract_id_by_txn_type(txn_type)}/metadata.json"))


def list_all_contract_ids() -> List[str]:
    query_result = elasticsearch.list_document_ids(index=elasticsearch.Indexes.smartcontract.value)
    contract_ids = []
    for contract_id in query_result:
        contract_ids.append(contract_id)
    return contract_ids


def get_serial_contracts() -> List[smart_contract_model.SmartContractModel]:
    """
    Searches for serial contracts
    Please note this function fetches all smart contract metadata from storage each time it is run, so should be used sparingly
    """
    # First check and remove bad contracts or this function could fail
    return elasticsearch.search(index=elasticsearch.Indexes.smartcontract.value, query={"query": {"match_phrase": {"execution_order": "serial"}}})["results"]


def remove_bad_contracts() -> None:
    """Remove contract(s) from the index if its metadata doesn't exist"""
    for sc_id in list_all_contract_ids():
        try:
            get_contract_by_id(sc_id)
        except exceptions.NotFound:
            elasticsearch.delete_document(index=elasticsearch.Indexes.smartcontract.value, doc_id=sc_id)


def add_smart_contract_index(contract: smart_contract_model.SmartContractModel) -> None:
    """Add the index for a smart contract"""
    elasticsearch.put_document(elasticsearch.Indexes.smartcontract.value, {"sc_name": contract.txn_type}, contract.id)


def remove_smart_contract_index(contract_id: str) -> None:
    """Remove the index for a smart contract"""
    elasticsearch.delete_document(elasticsearch.Indexes.smartcontract.value, contract_id)


def get_contract_by_id(contract_id: str) -> smart_contract_model.SmartContractModel:
    """Searches for a contract by contract_id"""
    return smart_contract_model.new_from_at_rest(storage.get_json_from_object(f"{FOLDER}/{contract_id}/metadata.json"))


def contract_does_exist(contract_id: str) -> bool:
    """Checks if a contract exists or not"""
    return storage.does_object_exist(f"{FOLDER}/{contract_id}/metadata.json")


def get_contract_logs(contract_id, since: Optional[str], tail: Optional[int]) -> List[Dict[str, str]]:
    """Returns a list of smart contract logs from openfaas"""
    return faas.get_logs(contract_id, since, tail)

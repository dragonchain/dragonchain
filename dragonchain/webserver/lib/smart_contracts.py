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

import os
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from dragonchain import logger
from dragonchain import exceptions
from dragonchain import job_processor
from dragonchain.lib.dao import transaction_type_dao
from dragonchain.lib.dao import smart_contract_dao
from dragonchain.lib.dto import smart_contract_model
from dragonchain.lib.database import elasticsearch
from dragonchain.lib.interfaces import storage

if TYPE_CHECKING:
    from dragonchain.lib.types import ESSearch

_log = logger.get_logger()

MAX_CONTRACT_LIMIT = int(os.environ["MAX_CONTRACT_LIMIT"]) if os.environ.get("MAX_CONTRACT_LIMIT") else 20


def get_by_id_v1(smart_contract_id: str) -> Dict[str, Any]:
    return storage.get_json_from_object(f"{smart_contract_dao.FOLDER}/{smart_contract_id}/metadata.json")


def get_by_txn_type_v1(txn_type: str) -> Dict[str, Any]:
    results = elasticsearch.search(folder=smart_contract_dao.FOLDER, query={"query": {"match_phrase": {"txn_type": txn_type}}})["results"]
    if results:
        return results[0]
    raise exceptions.NotFound(f"Smart contract {txn_type} could not be found.")


def query_contracts_v1(params: Optional[dict]) -> "ESSearch":
    """Lambda function used by the smartcontract endpoint with method GET.
        Returns smart contracts matching SC txn_type, with query parameters accepted.
    Args:
        contract_id (str, exclusive): SC contract_id to search for.
        txn_type (str, exclusive): SC txn_type to search for.
        params (dict, exclusive): Dict of params for Elastic searching.
    Returns:
        The Elastic search results of the query specified.
    """
    if params:
        query_params = params.get("q") or "*"  # default to returning all results (limit 10 by default)
        sort_param = params.get("sort") or None
        limit_param = params.get("limit") or None
        offset_param = params.get("offset") or None

        _log.info(f"QUERY STRING PARAMS FOUND: {query_params}")
        return elasticsearch.search(folder=smart_contract_dao.FOLDER, q=query_params, sort=sort_param, limit=limit_param, offset=offset_param)
    else:
        return elasticsearch.search(folder=smart_contract_dao.FOLDER, q="*")


def create_contract_v1(body: dict) -> dict:
    """Deploy a new contract on the chain
    Args:
        body: The parsed body, supplied by user. This is used to create a data model
    Returns:
        DTO of the contract at rest which is being created
    """
    # Before anything else, check to see if this chain has too many contracts
    if elasticsearch.get_count(folder=smart_contract_dao.FOLDER) >= MAX_CONTRACT_LIMIT:
        raise exceptions.ContractLimitExceeded(MAX_CONTRACT_LIMIT)
    # Create model and validate fields
    _log.info(f"Creating data model for {body['txn_type']}")
    contract = smart_contract_model.new_contract_from_user(body)

    # Register new trasnsaction type for smart contract
    _log.info("Registering new smart contract transaction type")
    transaction_type_dao.register_smart_contract_transaction_type(contract)

    # Start build task
    try:
        job_processor.begin_task(contract, task_type=smart_contract_model.ContractActions.CREATE)
    except RuntimeError:
        transaction_type_dao.remove_existing_transaction_type(contract.txn_type)
        raise
    return contract.export_as_at_rest()


def update_contract_v1(contract_id: str, update: dict) -> dict:
    """Update an existing contract on the chain
    Args:
        contract_id: The contract_id of the contract
        update: The parsed body, supplied by user. This is used to create an update data model
    Returns:
        DTO of the contract at rest which has been updated
    """
    # Get existing model, and check state
    contract = smart_contract_dao.get_contract_by_id(contract_id)
    contract_update = smart_contract_model.new_update_contract(update, existing_contract=contract)
    if smart_contract_model.ContractState.is_updatable_state(contract.status["state"]):
        raise exceptions.BadStateError(f'State {contract.status["state"]} not valid to begin updates')

    # Create and validate update model
    contract_update.start_state = contract.status["state"]

    # Set state to updating
    contract.set_state(smart_contract_model.ContractState.UPDATING)
    contract.save()

    try:
        job_processor.begin_task(contract_update, task_type=smart_contract_model.ContractActions.UPDATE)
    except RuntimeError:
        contract.set_state(state=smart_contract_model.ContractState.ACTIVE, msg="Contract update failed: could not start update.")
        contract.save()
        raise
    return contract.export_as_at_rest()


def delete_contract_v1(contract_id: str) -> None:
    """Delete a contract
    Args:
        contract_id (str): The contract_id of the contract
    Returns:
        smart contract at rest which was deleted
    """
    _log.info(f"Getting contract {contract_id} to delete")
    contract = smart_contract_dao.get_contract_by_id(contract_id)
    _log.info("Setting delete state..")
    contract.set_state(smart_contract_model.ContractState.DELETING)
    contract.save()

    try:
        job_processor.begin_task(contract, task_type=smart_contract_model.ContractActions.DELETE)
    except RuntimeError:
        _log.exception("Could not begin delete, rolling back state.")
        contract.set_state(state=smart_contract_model.ContractState.ACTIVE, msg="Contract delete failed: could not start deletion")
        contract.save()
        raise


def heap_list_v1(contract_id: str, path: str) -> List[str]:
    sub_folder = f"{contract_id}/HEAP"
    storage_key = f"{smart_contract_dao.FOLDER}/{sub_folder}{path}"
    listed_keys = storage.list_objects(storage_key)
    key_response = []
    for key in listed_keys:
        key_response.append(key[key.index(sub_folder) + len(sub_folder) :])
    return key_response


def heap_get_v1(contract_id: str, path: str) -> str:
    storage_key = f"{smart_contract_dao.FOLDER}/{contract_id}/HEAP{path}"
    return storage.get(key=storage_key).decode("utf-8")

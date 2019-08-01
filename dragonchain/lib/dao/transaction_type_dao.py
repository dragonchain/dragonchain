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

from typing import cast, List, Dict, TYPE_CHECKING

from dragonchain.lib.interfaces import storage
from dragonchain.lib.dto import transaction_type_model
from dragonchain.lib.database import redis
from dragonchain import logger
from dragonchain import exceptions

if TYPE_CHECKING:
    from dragonchain.lib.dto import smart_contract_model

FOLDER = "TRANSACTION_TYPES"
TYPE_LIST_KEY = "type_list_key"

_log = logger.get_logger()


def get_registered_transaction_type(transaction_type: str) -> transaction_type_model.TransactionTypeModel:
    """
    Searches for a registered transaction type by name
    :param transaction_type
    """
    _log.info(f"Attempting to get type {transaction_type}")
    result = storage.get_json_from_object(f"{FOLDER}/TYPES/{transaction_type}")
    return transaction_type_model.new_from_at_rest(result)


def get_registered_transaction_types_or_default(transaction_types: List[str]) -> Dict[str, transaction_type_model.TransactionTypeModel]:
    """Bulk get of registered transaction types
       Note: If a transaction type is not found, it is sent back as a TransactionTypeModel with default values
    Args:
        transaction_types: a list of transaction types to fetch models for
    Returns:
        dictionary with key being txn_type and value being of type TransactionTypeModel
    """
    transaction_type_object: Dict[str, transaction_type_model.TransactionTypeModel] = {}
    for txn_type in transaction_types:
        if txn_type not in transaction_type_object and not txn_type.startswith("-SYSTEM"):
            try:
                transaction_type_object[txn_type] = get_registered_transaction_type(txn_type)
            except exceptions.NotFound:
                # Use a 'default' TransactionTypeModel if we couldn't find an existing matching txn_type
                transaction_type_object[txn_type] = transaction_type_model.TransactionTypeModel(
                    txn_type=txn_type, custom_indexes=[], contract_id=False
                )
    return transaction_type_object


def remove_existing_transaction_type(transaction_type: str) -> None:
    """
    Deletes a registered transaction type if not contract
    """
    _log.info(f"Deleting existing transaction type {transaction_type}")
    redis.srem_sync(TYPE_LIST_KEY, transaction_type)
    storage.delete(f"{FOLDER}/TYPES/{transaction_type}")


def rehydrate_transaction_types() -> None:
    existing_list = redis.smembers_sync("type_list_key")
    if len(existing_list) > 0:
        _log.info("redis is already populated")
        return

    transaction_types = filter(lambda x: len(x.split("/")) == 3, storage.list_objects("TRANSACTION_TYPES"))
    txn_types = list(map(lambda x: x.split("/")[2], transaction_types))
    _log.info("Inserting new list into redis")
    if len(txn_types) > 0:
        response_number = redis.sadd_sync("type_list_key", *txn_types)
        if response_number > 0:
            _log.info("Succeeded in updating redis")
        _log.info(f"response number --> {response_number}")
    else:
        _log.info("No transaction types found to be updated...")


def register_smart_contract_transaction_type(smart_contract_model: "smart_contract_model.SmartContractModel") -> None:
    """Creates a new transaction type for a contract. Throws ContractConflict exception if name exists
    Args:
        model (obj): The model of the contract
    Returns:
        None if no duplicates are found, or throws ContractConflict
    Raises:
        TransactionTypeConflict exception if name exists
    """
    try:
        get_registered_transaction_type(smart_contract_model.txn_type)
        raise exceptions.TransactionTypeConflict("Transaction type already registered")
    except exceptions.NotFound:
        pass

    _log.debug("Uploading new contract type to datastore")
    txn_type_model = transaction_type_model.new_from_contract_create(smart_contract_model.txn_type, smart_contract_model.id)
    store_registered_transaction_type(txn_type_model)


def store_registered_transaction_type(transaction_type_model: transaction_type_model.TransactionTypeModel) -> None:
    """
    Stores a new transaction type
    """
    _log.info("Uploading to datastore")
    storage.put_object_as_json(f"{FOLDER}/TYPES/{transaction_type_model.txn_type}", transaction_type_model.export_as_at_rest())
    redis.sadd_sync(TYPE_LIST_KEY, cast(str, transaction_type_model.txn_type))  # This should defined when passed in
    _log.info("Successfully uploaded new transaction type to datastore")

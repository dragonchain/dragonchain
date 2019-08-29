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

from typing import Dict, Any, List, Iterable, Optional, TYPE_CHECKING

from dragonchain.lib.interfaces import storage
from dragonchain.lib.dto import transaction_type_model
from dragonchain.lib.database import redis
from dragonchain.lib.database import redisearch
from dragonchain import logger
from dragonchain import exceptions

if TYPE_CHECKING:
    from dragonchain.lib.dto import smart_contract_model
    from dragonchain.lib.types import custom_index  # noqa: F401

FOLDER = "TRANSACTION_TYPES/TYPES"
QUEUED_TXN_TYPES = "mq:txn_type_creation_queue"

_log = logger.get_logger()


def get_registered_transaction_type(transaction_type: str) -> transaction_type_model.TransactionTypeModel:
    """
    Searches for a registered transaction type by name
    :param transaction_type
    """
    _log.info(f"Attempting to get type {transaction_type}")
    result = storage.get_json_from_object(f"{FOLDER}/{transaction_type}")
    return transaction_type_model.new_from_at_rest(result)


def get_registered_transaction_types_or_default(transaction_types: Iterable[str]) -> Dict[str, transaction_type_model.TransactionTypeModel]:
    """Bulk get of registered transaction types
       Note: If a transaction type is not found, it is sent back as a TransactionTypeModel with default values
    Args:
        transaction_types: a list of transaction types to fetch models for
    Returns:
        dictionary with key being txn_type and value being of its TransactionTypeModel
    """
    transaction_type_object: Dict[str, transaction_type_model.TransactionTypeModel] = {}
    for txn_type in transaction_types:
        if txn_type not in transaction_type_object and not txn_type.startswith("-SYSTEM"):
            try:
                transaction_type_object[txn_type] = get_registered_transaction_type(txn_type)
            except exceptions.NotFound:
                # Use a 'default' TransactionTypeModel if we couldn't find an existing matching txn_type
                transaction_type_object[txn_type] = transaction_type_model.TransactionTypeModel(txn_type=txn_type, active_since_block="1")
    return transaction_type_object


def list_registered_transaction_types() -> List[Dict[str, Any]]:
    return [storage.get_json_from_object(txn_type) for txn_type in storage.list_objects(f"{FOLDER}/")]


def remove_existing_transaction_type(transaction_type: str) -> None:
    """
    Deletes a registered transaction type
    """
    _log.info(f"Deleting existing transaction type {transaction_type}")
    redisearch.delete_index(transaction_type)
    storage.delete(f"{FOLDER}/{transaction_type}")


def register_smart_contract_transaction_type(
    sc_model: "smart_contract_model.SmartContractModel", custom_indexes: Optional[List["custom_index"]]
) -> None:
    """Creates a new transaction type for a contract. Throws ContractConflict exception if name exists
    Args:
        smart_contract_model: The model of the contract
        custom_indexes: A list of the custom indexes for the transaction type for the contract (if any)
    """
    _log.debug("Queueing new contract type")
    txn_type_model = transaction_type_model.new_from_contract_create(sc_model.txn_type, sc_model.id, custom_indexes)
    create_new_transaction_type(txn_type_model)


def activate_transaction_types_if_necessary(block_id: str) -> None:
    """Activate transaction type(s) by setting them to active at a certain block number (for index regeneration purposes)
    Args:
        block_id: the current block id where the transaction types are being activated (if they exist)
    """
    # Get all the queued transaction types
    p = redis.pipeline_sync(transaction=True)
    p.lrange(QUEUED_TXN_TYPES, 0, -1)
    p.delete(QUEUED_TXN_TYPES)
    results, _ = p.execute()
    for txn_type in results:
        try:
            txn_type_model = get_registered_transaction_type(txn_type.decode("utf8"))
            txn_type_model.active_since_block = block_id
            # Save the transaction type state
            storage.put_object_as_json(f"{FOLDER}/{txn_type_model.txn_type}", txn_type_model.export_as_at_rest())
        except exceptions.NotFound:
            pass  # txn_type was probably deleted before activating. Simply ignore it


def create_new_transaction_type(txn_type_model: transaction_type_model.TransactionTypeModel) -> None:
    """Save a new transaction type model"""
    txn_type_dto = txn_type_model.export_as_at_rest()
    _log.info(f"Adding transaction index for {txn_type_model.txn_type}")
    redisearch.force_create_transaction_index(txn_type_model.txn_type, txn_type_model.custom_indexes)
    _log.debug(f"Queuing for activation")
    redis.lpush_sync(QUEUED_TXN_TYPES, txn_type_model.txn_type)
    _log.debug(f"Adding the transaction type to storage")
    storage.put_object_as_json(f"{FOLDER}/{txn_type_model.txn_type}", txn_type_dto)

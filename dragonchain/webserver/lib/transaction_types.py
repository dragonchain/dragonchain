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

from typing import Dict, Any, TYPE_CHECKING

from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib.dto import transaction_type_model
from dragonchain.lib.dao import transaction_type_dao
from dragonchain.lib.dao import smart_contract_dao
from dragonchain.lib.interfaces import storage

if TYPE_CHECKING:
    from dragonchain.lib.types import custom_index  # noqa: F401 used for typing

_log = logger.get_logger()


def list_registered_transaction_types_v1() -> Dict[str, Any]:
    """
    Lists out the current registered transaction types
    """
    _log.info("Listing out existing transaction types")
    return {"transaction_types": transaction_type_dao.list_registered_transaction_types()}


def register_transaction_type_v1(transaction_type_structure: Dict[str, Any]) -> None:
    """
    Takes in a transaction type structure and attempts to register
    """
    model = transaction_type_model.new_from_user_input(transaction_type_structure)
    try:
        transaction_type_dao.get_registered_transaction_type(model.txn_type)
    except exceptions.NotFound:
        pass
    else:
        _log.error("Transaction type is already registered")
        raise exceptions.TransactionTypeConflict(f"A transaction type of {model.txn_type} is already registered")
    _log.debug("Queuing transaction type for creation")
    transaction_type_dao.create_new_transaction_type(model)


def delete_transaction_type_v1(transaction_type: str) -> None:
    """
    Takes in a transaction type
    Checks if the transaction type is of smart contract
    Deletes type
    """
    try:
        existing_txn_type = transaction_type_dao.get_registered_transaction_type(transaction_type)
        # If txn type is a smart contract that exists, don't allow it to be deleted
        if existing_txn_type.contract_id and smart_contract_dao.contract_does_exist(existing_txn_type.contract_id):
            raise exceptions.ActionForbidden("Cannot delete smart contract transaction type")
        transaction_type_dao.remove_existing_transaction_type(transaction_type)
    except exceptions.NotFound:
        return


def get_transaction_type_v1(transaction_type: str) -> Dict[str, Any]:
    return storage.get_json_from_object(f"{transaction_type_dao.FOLDER}/{transaction_type}")

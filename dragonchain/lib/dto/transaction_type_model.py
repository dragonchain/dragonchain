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

from typing import Optional, Union, List, Dict, Any, TYPE_CHECKING

from dragonchain.lib.dto import model
from dragonchain import logger

if TYPE_CHECKING:
    from dragonchain.lib.types import custom_index  # noqa: F401 used with types

_log = logger.get_logger()


def new_from_user_input(user_input: Dict[str, Any]) -> "TransactionTypeModel":
    """
    Construct a transaction type model from user creation request
    """
    if user_input.get("version") == "1":
        return TransactionTypeModel(txn_type=user_input["txn_type"], custom_indexes=user_input.get("custom_indexes") or [], contract_id=False)
    else:
        raise NotImplementedError(f"Version {user_input.get('version')} is not supported")


def new_from_at_rest(transaction_type_data: Dict[str, Any]) -> "TransactionTypeModel":
    """
    Construct a transaction type model from at rest (cached storage)
    """
    if transaction_type_data.get("version") == "1":
        return TransactionTypeModel(
            txn_type=transaction_type_data["txn_type"],
            custom_indexes=transaction_type_data["custom_indexes"],
            contract_id=transaction_type_data.get("contract_id"),
        )
    else:
        raise NotImplementedError(f"Version {transaction_type_data.get('version')} is not supported")


def new_from_contract_create(txn_type: str, contract_id: str) -> "TransactionTypeModel":
    return TransactionTypeModel(txn_type=txn_type, contract_id=contract_id)


class TransactionTypeModel(model.Model):
    """
    TransactionTypeModel class is a representation of transaction type information
    """

    def __init__(
        self, txn_type: Optional[str] = None, custom_indexes: Optional[List["custom_index"]] = None, contract_id: Optional[Union[str, bool]] = None
    ):
        self.txn_type = txn_type
        self.custom_indexes = custom_indexes or []
        self.contract_id = contract_id

    def export_as_at_rest(self) -> Dict[str, Any]:
        return {"version": "1", "txn_type": self.txn_type, "custom_indexes": self.custom_indexes, "contract_id": self.contract_id}

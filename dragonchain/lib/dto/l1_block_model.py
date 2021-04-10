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

import time
import json
import math
from typing import Dict, Any, List, Set, TYPE_CHECKING

import fastjsonschema

from dragonchain.lib.interfaces import storage
from dragonchain.lib.dto import transaction_model
from dragonchain.lib.dto import schema
from dragonchain.lib.dto import model
from dragonchain.lib import keys

if TYPE_CHECKING:
    from dragonchain.lib.dto import transaction_type_model  # noqa: F401

EPOCH_OFFSET = 1432238220
BLOCK_INTERVAL = 5

_validate_l1_block_at_rest = fastjsonschema.compile(schema.l1_block_at_rest_schema)


def new_from_full_transactions(
    full_transactions_array: List[transaction_model.TransactionModel], block_id: str, prev_id: str, prev_proof: str
) -> "L1BlockModel":
    """
    Used in creating new blocks
    Input: List of TransactionModels, previous ID and proof
    Returns: BlockModel object
    """
    # Check the types of input, as there is no schema for a list of full transactions
    if not isinstance(full_transactions_array, list):
        raise TypeError("Invalid input types to create new block model.")

    # Assign the current block ID to every transaction
    for transaction in full_transactions_array:
        if not isinstance(transaction, transaction_model.TransactionModel):
            raise TypeError("Invalid input types to create new block model.")
        transaction.block_id = block_id

    return L1BlockModel(
        dc_id=keys.get_public_id(),
        block_id=block_id,
        timestamp=str(math.floor(time.time())),
        prev_proof=prev_proof,
        prev_id=prev_id,
        transactions=full_transactions_array,
    )


def new_from_stripped_block(stripped_block: Dict[str, Any]) -> "L1BlockModel":
    """
    Used in querying from the DAO
    Input: Block::L1::AtRest DTO
    Returns: BlockModel object
    """
    # Validate inputted schema
    _validate_l1_block_at_rest(stripped_block)
    if stripped_block.get("version") == "1":
        return L1BlockModel(
            dc_id=stripped_block["header"]["dc_id"],
            block_id=stripped_block["header"]["block_id"],
            timestamp=stripped_block["header"].get("timestamp") or "-1",
            prev_proof=stripped_block["header"]["prev_proof"],
            prev_id=stripped_block["header"]["prev_id"],
            stripped_transactions=stripped_block["transactions"],
            scheme=stripped_block["proof"]["scheme"],
            proof=stripped_block["proof"]["proof"],
            nonce=stripped_block["proof"].get("nonce"),
        )
    else:
        raise NotImplementedError("Only version 1 DTO of stripped blocks are supported")


def get_current_block_id() -> str:
    # get the seconds in 5 sec intervals
    # interval = int(now.gmtime().tm_sec / BLOCK_INTERVAL) * BLOCK_INTERVAL
    return str(int((time.time() - EPOCH_OFFSET) / BLOCK_INTERVAL))


def export_broadcast_dto(block: Dict[str, Any]) -> Dict[str, Any]:
    return {"version": "1", "payload": block}


class L1BlockModel(model.BlockModel):
    """
    L1BlockModel class is an abstracted representation of an l1 block object
    """

    def __init__(
        self,
        dc_id=None,
        block_id=None,
        timestamp=None,
        prev_proof="",
        prev_id="",
        transactions=None,
        stripped_transactions=None,
        scheme="",
        proof="",
        nonce=None,
    ):
        """L1BlockModel Constructor"""
        self.dc_id = dc_id
        self.block_id = block_id
        self.timestamp = timestamp
        self.prev_proof = prev_proof
        self.prev_id = prev_id
        self.transactions = transactions or []
        self.stripped_transactions = stripped_transactions or []
        self.scheme = scheme
        self.proof = proof
        self.nonce = nonce

    def strip_payloads(self) -> None:
        """Generate stringified stripped_transactions array for storage in storage"""
        # Clear stripped transactions before setting
        if self.transactions:
            self.stripped_transactions = []
        for transaction in self.transactions:
            self.stripped_transactions.append(json.dumps(transaction.export_as_stripped(), separators=(",", ":")))

    def get_associated_l1_dcid(self) -> str:
        """Interface function for compatibility"""
        return self.dc_id

    def get_associated_l1_block_id(self) -> Set[str]:
        """Interface function for compatibility"""
        return {self.block_id}

    def get_txn_types(self) -> List[str]:
        """Returns unique list of transaction types from block"""
        return list({transaction.txn_type for transaction in self.transactions})

    def set_custom_indexes(self, transaction_type_models: Dict[str, "transaction_type_model.TransactionTypeModel"]) -> None:
        """Sets the custom indexing on each instance of TransactionModel"""
        for transaction in self.transactions:
            if not transaction.txn_type.startswith("-SYSTEM"):
                transaction.extract_custom_indexes(transaction_type_models[transaction.txn_type])

    def export_as_at_rest(self) -> Dict[str, Any]:
        """Export as block at rest DTO"""
        if len(self.stripped_transactions) == 0:
            self.strip_payloads()
        proof = None
        if self.scheme == "trust":
            proof = {"scheme": self.scheme, "proof": self.proof}
        else:
            proof = {"scheme": self.scheme, "proof": self.proof, "nonce": self.nonce}
        return {
            "version": "1",
            "dcrn": schema.DCRN.Block_L1_At_Rest.value,
            "header": {
                "dc_id": self.dc_id,
                "block_id": self.block_id,
                "level": 1,
                "timestamp": self.timestamp,
                "prev_id": self.prev_id,
                "prev_proof": self.prev_proof,
            },
            "transactions": self.stripped_transactions,
            "proof": proof,
        }

    def export_as_full_transactions(self) -> str:
        """Export full transactions in block as NDJSON (for storage select when querying)"""
        txn_string = ""
        for transaction in self.transactions:
            txn_string += '{"txn_id": "' + transaction.txn_id + '", "stripped_payload_by_block": true, '
            txn_string += '"txn": ' + json.dumps(transaction.export_as_full(), separators=(",", ":")) + "}\n"
        return txn_string

    def store_transaction_payloads(self) -> None:
        """Stores full transaction payloads for block"""
        payloads: dict = {}
        for transaction in self.transactions:
            payloads[transaction.txn_id] = json.dumps(transaction.payload, separators=(",", ":")).encode("utf-8")
        storage.put(f"PAYLOADS/{self.block_id}", json.dumps(payloads, separators=(",", ":")).encode("utf-8"))

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

import json
from typing import TYPE_CHECKING, Mapping, Any

from jsonpath import jsonpath

from dragonchain.lib.dto import schema
from dragonchain.lib.dto import model
from dragonchain import logger

if TYPE_CHECKING:
    from dragonchain.lib.dto import transaction_type_model

_log = logger.get_logger()


def new_from_user_input(create_task: Mapping[str, Any]) -> "TransactionModel":
    """
    Construct a transaction model from user given information.
    Presumes input has already been sanitized.
    """
    if create_task.get("version") == "1":
        return TransactionModel(txn_type=create_task["txn_type"], payload=create_task["payload"], tag=create_task.get("tag") or "")
    else:
        raise NotImplementedError(f"Version {create_task.get('version')} is not supported")


def new_from_queue_input(queue_task: Mapping[str, Any]) -> "TransactionModel":
    """
    Construct a transaction model from a DTO popped off the queue.
    """
    if queue_task.get("version") == "2" or queue_task.get("version") == "1":  # apparently these are identical
        return TransactionModel(
            txn_type=queue_task["header"]["txn_type"],
            dc_id=queue_task["header"]["dc_id"],
            txn_id=queue_task["header"]["txn_id"],
            timestamp=queue_task["header"]["timestamp"],
            payload=queue_task["payload"],
            tag=queue_task["header"].get("tag") or "",
            invoker=queue_task["header"].get("invoker") or "",
        )
    else:
        raise NotImplementedError(f"Version {queue_task.get('version')} is not supported")


def new_from_stripped_block_input(l1_block_txn: str) -> "TransactionModel":
    """Construct a transaction model from an l1 stripped block txn
    Args:
        l1_block_txn: stringified json of transaction from a stripped block
    Returns:
        Instantiated TransactionModel
    Raises:
        NotImplementedError when dto version isn't supported
    """
    txn = json.loads(l1_block_txn)
    if txn.get("version") == "2":
        return TransactionModel(
            dc_id=txn["header"]["dc_id"],
            block_id=txn["header"]["block_id"],
            txn_id=txn["header"]["txn_id"],
            timestamp=txn["header"]["timestamp"],
            txn_type=txn["header"]["txn_type"],
            tag=txn["header"]["tag"],
            invoker=txn["header"]["invoker"],
            full_hash=txn["proof"]["full"],
            signature=txn["proof"]["stripped"],
        )
    else:
        raise NotImplementedError(f"Version {txn.get('version')} is not supported")


class TransactionModel(model.Model):
    """
    TransactionModel class is an abstracted representation of a transaction object
    """

    def __init__(
        self,
        dc_id=None,
        block_id=None,
        txn_id=None,
        timestamp=None,
        txn_type=None,
        tag: str = "",
        payload="",
        signature=None,
        full_hash=None,
        invoker: str = "",
    ):
        """Model Constructor"""
        self.dc_id = dc_id
        self.block_id = block_id
        self.txn_id = txn_id
        self.timestamp = timestamp
        self.txn_type = txn_type
        self.tag = tag
        self.payload = payload
        self.signature = signature
        self.full_hash = full_hash
        self.invoker = invoker
        self.custom_indexed_data: dict = {}

    def export_as_full(self) -> dict:
        """Export Transaction::L1::FullTransaction DTO"""
        return {
            "version": "2",
            "dcrn": schema.DCRN.Transaction_L1_Full.value,
            "header": {
                "txn_type": self.txn_type,
                "dc_id": self.dc_id,
                "txn_id": self.txn_id,
                "block_id": self.block_id,
                "timestamp": self.timestamp,
                "tag": self.tag or "",
                "invoker": self.invoker or "",
            },
            "payload": self.payload,
            "proof": {"full": self.full_hash, "stripped": self.signature},
        }

    def export_as_stripped(self) -> dict:
        """Export Transaction::L1::Stripped DTO"""
        return {
            "version": "2",
            "dcrn": schema.DCRN.Transaction_L1_Stripped.value,
            "header": {
                "txn_type": self.txn_type,
                "dc_id": self.dc_id,
                "txn_id": self.txn_id,
                "block_id": self.block_id,
                "timestamp": self.timestamp,
                "tag": self.tag or "",
                "invoker": self.invoker or "",
            },
            "proof": {"full": self.full_hash, "stripped": self.signature},
        }

    def export_as_queue_task(self, dict_payload: bool = False) -> dict:
        """Export Transaction::L1::QueueTask DTO"""
        return {
            "version": "2",
            "header": {
                "txn_type": self.txn_type,
                "dc_id": self.dc_id,
                "txn_id": self.txn_id,
                "timestamp": self.timestamp,
                "tag": self.tag or "",
                "invoker": self.invoker or "",
            },
            "payload": json.dumps(self.payload, separators=(",", ":")) if not dict_payload else self.payload,
        }

    def export_as_search_index(self, stub: bool = False) -> dict:
        """Export Transaction::L1::SearchIndex DTO"""
        search_indexes = {
            "version": "2",
            "status": "processed" if not stub else "pending",
            "dcrn": schema.DCRN.Transaction_L1_Search_Index.value,
            "txn_type": self.txn_type,
            "dc_id": self.dc_id,
            "txn_id": self.txn_id,
            "tag": self.tag or "",
            "block_id": int(self.block_id) if not stub else "",
            "timestamp": int(self.timestamp) if not stub else "",
            "invoker": self.invoker or "",
            "s3_object_folder": "TRANSACTION",
            "s3_object_id": str(self.block_id) if not stub else "",
            "l2_rejections": 0,
        }
        reserved_keywords = search_indexes.keys()
        for k, v in self.custom_indexed_data.items():
            if k not in reserved_keywords:
                search_indexes[k] = v if isinstance(v, str) else json.dumps(v, separators=(",", ":"))
            else:
                _log.info(f"[TXN MODEL] Requested index path: {k} is a reserved keyword")
        return {self.txn_id: search_indexes} if not stub else search_indexes

    def extract_custom_indexes(self, transaction_type_model: "transaction_type_model.TransactionTypeModel") -> None:
        """Extracts and formats custom indexed data paths from payload"""
        transaction_index_object = {}
        if len(transaction_type_model.custom_indexes) > 0:
            _log.debug(f"indexes: {transaction_type_model.custom_indexes}")
            for index in transaction_type_model.custom_indexes:
                key = index["key"]
                path = index["path"]
                _log.debug(f"index name: {key}, index path: {path}")
                try:
                    indexable_object = jsonpath(json.loads(self.payload), path)
                    _log.debug(f"indexable_object: {indexable_object}")
                    if indexable_object and isinstance(indexable_object, list) and len(indexable_object) == 1:
                        transaction_index_object[key] = indexable_object[0]
                except Exception:
                    # silence errors as we still want to continue processing as normal
                    _log.exception("Could not locate indexable object in payload")
        self.custom_indexed_data = transaction_index_object

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

import uuid
import time
from typing import TYPE_CHECKING

import redis

from dragonchain.lib.database import redisearch
from dragonchain.lib.interfaces import storage
from dragonchain.lib.dto import transaction_model
from dragonchain.lib import namespace
from dragonchain.lib import queue
from dragonchain.lib import keys
from dragonchain import logger

if TYPE_CHECKING:
    from dragonchain.lib.dto import l1_block_model

FOLDER = "TRANSACTION"
S3_OBJECT_ID = "s3_object_id"

_log = logger.get_logger()


def ledger_contract_action(action: str, txn_type: str, entrypoint: str, image_digest: str) -> None:
    """Ledgers contract data when submit contract is a success
    Args:
        action (Enum): Which action to perform when ledgering
        txn_type (str): Transaction type to post to the chain
        image_digest (str): Docker image SHA-256 to use in ledgering
    """
    model = transaction_model.TransactionModel(
        txn_type=namespace.Namespaces.Contract.value,
        dc_id=keys.get_public_id(),
        txn_id=str(uuid.uuid4()),
        tag=f"contract:{txn_type}",
        timestamp=str(int(time.time())),
        payload={"action": action, "txn_type": txn_type, "contract_entrypoint": entrypoint, "image_digest": image_digest},
    )
    queue.enqueue_generic(model.export_as_queue_task(), queue=queue.INCOMING_TX_KEY, deadline=0)


def store_full_txns(block_model: "l1_block_model.L1BlockModel") -> None:
    """
    Store the transactions object as a single file per block in storage.
    Also updates the indexes for each indexed transaction in ES with block information.
    """
    _log.info("[TRANSACTION DAO] Putting transaction to storage")
    storage.put(f"{FOLDER}/{block_model.block_id}", block_model.export_as_full_transactions().encode("utf-8"))
    # Could optimize by grouping indexing of transactions in the block with matchking txn_types using redisearch.put_many_documents
    for txn in block_model.transactions:
        redisearch.put_document(redisearch.Indexes.transaction.value, f"txn-{txn.txn_id}", {"block_id": txn.block_id}, upsert=True)
        try:
            redisearch.put_document(txn.txn_type, txn.txn_id, txn.export_as_search_index(), upsert=True)
        except redis.exceptions.ResponseError as e:
            # If the index doesn't exist, we don't care that we couldn't place the index (transaction type is probably deleted)
            if str(e) != "Unknown index name":
                raise
            else:
                _log.warning(f"Txn type {txn.txn_type} for txn {txn.txn_id} failed to index. (Transaction type may simply be deleted?) Ignoring")

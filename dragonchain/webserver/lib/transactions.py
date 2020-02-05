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

import uuid
import time
import math
import json
from typing import Sequence, Any, Dict, List, Optional, TYPE_CHECKING

import redis

from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib import keys
from dragonchain.lib import queue
from dragonchain.lib import callback
from dragonchain.lib.dto import transaction_model
from dragonchain.lib.interfaces import storage
from dragonchain.lib.database import redisearch
from dragonchain.lib.database import redis as dc_redis

if TYPE_CHECKING:
    from dragonchain.lib.types import RSearch
    from dragonchain.lib.dto import api_key_model

_log = logger.get_logger()


def _get_transaction_stub(txn_id: str) -> Dict[str, Any]:
    return {"header": {"txn_id": txn_id}, "status": "pending", "message": "This transaction is waiting to be included in a block"}


def query_transactions_v1(params: Dict[str, Any], parse: bool = True) -> "RSearch":
    """invoke queries on redisearch indexes
    Args:
        params: Dictionary of redisearch query options
        parse: If true, parse the transaction payload before returning
    Returns:
        {"results": [], "total": total} storage objects matching search query
    """
    if not params.get("transaction_type"):
        raise exceptions.ValidationException("transaction_type must be supplied for transaction queries")
    try:
        query_result = redisearch.search(
            index=params["transaction_type"],
            query_str=params["q"],
            only_id=params.get("id_only"),
            verbatim=params.get("verbatim"),
            offset=params.get("offset"),
            limit=params.get("limit"),
            sort_by=params.get("sort_by"),
            sort_asc=params.get("sort_asc"),
        )
    except redis.exceptions.ResponseError as e:
        error_str = str(e)
        # Detect if this is a syntax error; if so, throw it back as a 400 with the message
        if error_str.startswith("Syntax error"):
            raise exceptions.BadRequest(error_str)
        # If unknown index, user provided a bad transaction type
        elif error_str.endswith(": no such index"):
            raise exceptions.BadRequest("Invalid transaction type")
        else:
            raise
    result: "RSearch" = {"total": query_result.total, "results": []}
    if params.get("id_only"):
        result["results"] = [x.id for x in query_result.docs]
    else:
        transactions = []
        for doc in query_result.docs:
            block_id = doc.block_id
            transaction_id = doc.id
            retrieved_txn = storage.select_transaction(block_id, transaction_id)
            if parse:
                retrieved_txn["payload"] = json.loads(retrieved_txn["payload"])
            transactions.append(retrieved_txn)
        result["results"] = transactions
    return result


def get_transaction_v1(transaction_id: str, parse: bool = True) -> Dict[str, Any]:
    """
    get_transaction_by_id
    Searches for a transaction by a specific transaction ID
    """
    if dc_redis.sismember_sync(queue.TEMPORARY_TX_KEY, transaction_id):
        return _get_transaction_stub(transaction_id)
    doc = redisearch.get_document(redisearch.Indexes.transaction.value, f"txn-{transaction_id}")
    try:
        block_id = doc.block_id
    except AttributeError:
        raise exceptions.NotFound(f"Transaction {transaction_id} could not be found.")
    txn = storage.select_transaction(block_id, transaction_id)
    if parse:
        txn["payload"] = json.loads(txn["payload"])
    return txn


def submit_transaction_v1(transaction: Dict[str, Any], callback_url: Optional[str], api_key: "api_key_model.APIKeyModel") -> Dict[str, str]:
    """Formats and enqueues individual transaction (from user input) to the webserver queue
    Returns:
        String of the submitted transaction id
    """
    _log.info("[TRANSACTION] Parsing and loading user input")
    txn_model = _generate_transaction_model(transaction)

    # Check if allowed to create transaction of this type
    if not api_key.is_key_allowed("transactions", "create", "create_transaction", False, extra_data={"requested_types": {txn_model.txn_type}}):
        raise exceptions.ActionForbidden(f"API Key is not allowed to create transaction of type {txn_model.txn_type}")

    _log.info("[TRANSACTION] Txn valid. Queueing txn object")
    queue.enqueue_item(txn_model.export_as_queue_task())

    if callback_url:
        _log.info("[TRANSACTION] Registering callback for queued txn")
        callback.register_callback(txn_model.txn_id, callback_url)

    return {"transaction_id": txn_model.txn_id}


def submit_bulk_transaction_v1(bulk_transaction: Sequence[Dict[str, Any]], api_key: "api_key_model.APIKeyModel") -> Dict[str, List[Any]]:
    """
    Formats, validates and enqueues the transactions in
    the payload of bulk_transaction
    Returns dictionary of 2 lists, key "201" are successfully created txn ids and key "400" are transactions that failed to post (entire dto passed in from user)
    """
    _log.info("[TRANSACTION_BULK] Checking if key is allowed to create all given bulk transactions")
    requested_types = set()
    for transaction in bulk_transaction:
        requested_types.add(transaction["txn_type"])
    # Check if allowed to create all these transactions of (potentially) various types
    if not api_key.is_key_allowed("transactions", "create", "create_transaction", False, extra_data={"requested_types": requested_types}):
        raise exceptions.ActionForbidden("API Key is not allowed to create all of the provided transaction types")

    _log.info(f"[TRANSACTION_BULK] Auth successful. Attempting to enqueue {len(bulk_transaction)} transactions")
    success = []
    fail = []
    pipeline = dc_redis.pipeline_sync()
    for transaction in bulk_transaction:
        try:
            txn_model = _generate_transaction_model(transaction)
            queue.enqueue_l1_pipeline(pipeline, txn_model.export_as_queue_task())
            success.append(txn_model.txn_id)
        except Exception:
            fail.append(transaction)
    # Queue the actual transactions in redis now
    for result in pipeline.execute():
        if not result:
            raise RuntimeError("Failed to enqueue")

    return {"201": success, "400": fail}


def _generate_transaction_model(transaction: Dict[str, Any]) -> transaction_model.TransactionModel:
    """
    Returns a transaction_model.TransactionModel instance with
    Dragonchain ID, Transaction ID, and Transaction timestamp
    """
    txn_model = transaction_model.new_from_user_input(transaction)
    txn_model.dc_id = keys.get_public_id()
    txn_model.txn_id = str(uuid.uuid4())
    txn_model.timestamp = str(math.floor(time.time()))
    return txn_model

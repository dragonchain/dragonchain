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
import math
import json
from typing import Sequence, Any, Dict, List, Optional, TYPE_CHECKING

from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib import keys
from dragonchain.lib import queue
from dragonchain.lib import callback
from dragonchain.lib.dto import transaction_model
from dragonchain.lib.dao import transaction_dao
from dragonchain.lib.interfaces import storage
from dragonchain.lib.database import elasticsearch

if TYPE_CHECKING:
    from dragonchain.lib.types import ESSearch

_log = logger.get_logger()


def query_transactions_v1(params: Optional[dict], parse: bool) -> "ESSearch":
    """Returns all transactions matching transaction id, with query parameters accepted.
    Args:
        params: dict of query params
        parse: whether or not to parse the response
    """
    if params:
        query_params = params.get("q") or "*"  # default to returning all results (limit 10 by default)
        sort_param = params.get("sort") or "block_id:desc"
        limit_param = params.get("limit") or None
        offset_param = params.get("offset") or None

        _log.info(f"[TRANSACTION] Query string params found: {query_params}")
        return _search_transaction(q=query_params, sort=sort_param, limit=limit_param, offset=offset_param, should_parse=parse)
    else:
        return _search_transaction(q="*", sort="block_id:desc", should_parse=parse)


def get_transaction_v1(transaction_id: str, parse: bool) -> dict:
    """
    get_transaction_by_id
    Searches for a transaction by a specific transaction ID
    """
    results = _search_transaction(query={"query": {"match_phrase": {"txn_id": transaction_id}}}, should_parse=parse)["results"]
    if results:
        return results[0]
    raise exceptions.NotFound(f"Transaction {transaction_id} could not be found.")


def submit_transaction_v1(transaction: Dict[str, Any], callback_url: Optional[str] = None) -> Dict[str, str]:
    """Formats and enqueues individual transaction (from user input) to the webserver queue
    Returns:
        String of the submitted transaction id
    """
    _log.info("[TRANSACTION] Parsing and loading user input")
    txn_model = _generate_transaction_model(transaction)

    _log.info("[TRANSACTION] Txn valid. Queueing txn object")
    queue.enqueue_item(txn_model.export_as_queue_task())

    _log.info("[TRANSACTION] insert transaction stub for pending transaction")
    _add_transaction_stub(txn_model)

    if callback_url:
        _log.info("[TRANSACTION] Registering callback for queued txn")
        callback.register_callback(txn_model.txn_id, callback_url)

    return {"transaction_id": txn_model.txn_id}


def submit_bulk_transaction_v1(bulk_transaction: Sequence[Dict[str, Any]]) -> Dict[str, List[Any]]:
    """
    Formats, validates and enqueues the transactions in
    the payload of bulk_transaction
    Returns tuple of 2 lists, index 0 is successful txn ids and index 1 are transactions that failed to post (entire dto passed in from user)
    """
    _log.info(f"[TRANSACTION_BULK] Attempting to enqueue {len(bulk_transaction)} transactions")
    success = []
    fail = []
    for transaction in bulk_transaction:
        try:
            _log.info("[TRANSACTION] Parsing and loading user input")
            txn_model = _generate_transaction_model(transaction)

            _log.info("[TRANSACTION] Txn valid. Queueing txn object")
            queue.enqueue_item(txn_model.export_as_queue_task())
            _log.info("[TRANSACTION] insert transaction stub for pending transaction")
            _add_transaction_stub(txn_model)
            success.append(txn_model.txn_id)
        except Exception:
            _log.exception("Processing transaction failed")
            fail.append(transaction)
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


def _search_transaction(
    query: Optional[dict] = None,
    q: Optional[str] = None,
    get_all: bool = False,
    sort: Optional[str] = None,
    offset: Optional[int] = None,
    limit: Optional[int] = None,
    should_parse: bool = True,
) -> "ESSearch":
    """invoke queries on elastic search indexes built with #set. Return the full storage stored object.
    Args:
        query: {dict=None} Elastic search query. The search definition using the ES Query DSL.
        q: {string=None} Query in the Lucene query string syntax
    Returns:
        {"results": [], "total": total} storage objects matching search query
    """
    hits_pages = elasticsearch.get_index_only(folder=transaction_dao.FOLDER, query=query, q=q, get_all=get_all, sort=sort, offset=offset, limit=limit)
    _log.info(f"pages: {hits_pages}")
    storage_objects = []

    for hit in hits_pages["hits"]:
        status = hit["_source"].get("status")
        if status == "pending":
            _log.info("[SEARCH TRANSACTION] FOUND PENDING TRANSACTION")
            stubbed_response = {
                "txn_id": hit["_source"]["txn_id"],
                "status": "pending",
                "message": "the transaction is waiting to be included into a block",
            }
            storage_objects.append(stubbed_response if should_parse else json.dumps(stubbed_response, separators=(",", ":")))
        else:
            storage_id = hit["_source"][transaction_dao.S3_OBJECT_ID]  # get the id
            storage_inner_id = hit["_source"]["txn_id"]  # get the transaction id to look for within the block
            storage_object = storage.select_transaction(storage_id, storage_inner_id)  # pull the object from storage, contained in a group file
            storage_objects.append(storage_object)  # add to the result set

            if should_parse:
                storage_object["payload"] = json.loads(storage_object["payload"])

    return {"results": storage_objects, "total": hits_pages["total"]}


def _add_transaction_stub(transaction_model: "transaction_model.TransactionModel") -> None:
    """store a stub for a transaction in elastic search to prevent 404s from querying
    Args:
        transaction_model: txn model to export search indexes from to store in ES
    """
    elasticsearch.put_index_only(transaction_dao.FOLDER, transaction_model.txn_id, transaction_model.export_as_search_index(stub=True))

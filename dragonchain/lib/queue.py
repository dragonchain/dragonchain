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
import json
import base64
from typing import List, Tuple, Union, Optional, Any, cast, TYPE_CHECKING

from dragonchain.lib import crypto
from dragonchain.lib.database import redis
from dragonchain.lib.dao import transaction_type_dao
from dragonchain.lib.dao import smart_contract_dao
from dragonchain.lib.dto import transaction_model
from dragonchain.lib.dto import l1_block_model
from dragonchain.lib.dto import l2_block_model
from dragonchain.lib.dto import l3_block_model
from dragonchain import logger
from dragonchain import exceptions

if TYPE_CHECKING:
    from dragonchain.lib.types import L1Headers


LEVEL = os.environ["LEVEL"]
REDIS_ENDPOINT = os.environ["REDIS_ENDPOINT"]
REDIS_PORT = os.environ["REDIS_PORT"]
INCOMING_TX_KEY = "dc:tx:incoming"
PROCESSING_TX_KEY = "dc:tx:processing"
CONTRACT_INVOKE_MQ_KEY = "mq:contract-invoke"

_log = logger.get_logger()


def check_and_recover_processing_if_necessary() -> None:
    """
    Checks the processing tx queue and returns them to the incoming queue
    (Should be called before starting to process a new block, for unexpected crash recovery)
    """
    if redis.llen_sync(PROCESSING_TX_KEY) != 0:
        _log.warning(
            "WARNING! Processing queue was not empty. Last block processing probably crashed. Recovering and re-queuing these dropped items."
        )
        to_recover = redis.lrange_sync(PROCESSING_TX_KEY, 0, -1, decode=False)
        # Execute these in a pipeline in attempts to make this as atomic as possible
        p = redis.pipeline_sync()
        p.rpush(INCOMING_TX_KEY, *to_recover)
        p.delete(PROCESSING_TX_KEY)
        p.execute()


def enqueue_item(item: dict, deadline: int = 0) -> None:
    """Enqueues to the chain's block / transaction queue"""
    if LEVEL == "1":
        return enqueue_l1(item)
    elif LEVEL == "2" or LEVEL == "3" or LEVEL == "4":
        return enqueue_generic(item["payload"], queue=INCOMING_TX_KEY, deadline=deadline)
    elif LEVEL == "5":
        return enqueue_generic(item["payload"], queue=INCOMING_TX_KEY, deadline=0)
    else:
        raise RuntimeError(f"Invalid level {LEVEL}")


def enqueue_l1(transaction: dict) -> None:
    txn_type_string = transaction["header"]["txn_type"]
    invocation_attempt = not transaction["header"].get("invoker")  # This transaction is an invocation attempt if there is no invoker

    try:
        transaction_type = transaction_type_dao.get_registered_transaction_type(txn_type_string)
    except exceptions.NotFound:
        _log.error("Invalid transaction type")
        raise exceptions.InvalidTransactionType(f"Transaction of type {txn_type_string} does not exist")

    # Enqueue to transaction queue
    enqueue_generic(transaction, queue=INCOMING_TX_KEY, deadline=0)

    # Attempt contract invocation if necessary
    if transaction_type.contract_id and invocation_attempt:
        _log.info("Checking if smart contract is associated with this txn_type")
        contract = smart_contract_dao.get_contract_by_id(transaction_type.contract_id)  # Explicitly checked for existence above
        contract_active = contract.status["state"] in ["active", "updating"]
        _log.info(f"Contract found: {contract}")

        if contract_active:
            transaction["payload"] = json.loads(transaction["payload"])  # We must parse the stringied payload of the SC invocation before sending
            invocation_request = contract.export_as_invoke_request(transaction)
            enqueue_generic(invocation_request, queue=CONTRACT_INVOKE_MQ_KEY, deadline=0)


def enqueue_generic(content: dict, queue: str, deadline: int) -> None:
    _log.info(f"Enqueueing content to {queue} queue")
    string_content = json.dumps(content, separators=(",", ":"))
    if not redis.lpush_sync(queue, string_content):
        raise RuntimeError("Failed to enqueue")
    if deadline:  # Set a deadline, beyond-which this L2-4 will disgard this item completely
        key = get_deadline_key(string_content.encode("utf8"))
        redis.set_sync(key, "a", deadline)  # Value is irrelevant


def is_not_empty() -> bool:
    """Check if there is another block in the queue ready to process"""
    return redis.llen_sync(INCOMING_TX_KEY) != 0


def clear_processing_queue() -> None:
    """Clear the processing queue after finishing processing a block successfully"""
    redis.delete_sync(PROCESSING_TX_KEY)


def get_deadline_key(item_as_bytes: bytes) -> str:
    unique_id = crypto.hash_bytes(crypto.SupportedHashes.sha256, item_as_bytes)
    return f"dc:tx:deadline:{base64.b64encode(unique_id).decode('ascii')}"


def item_is_expired(item_as_bytes: bytes) -> bool:
    """Check to see if the redis-key has expired yet. If so, this returns True."""
    return not redis.get_sync(get_deadline_key(item_as_bytes), decode=False)


def get_next_item() -> Optional[Any]:
    """Get and json.loads the next item from the queue"""
    item = cast(bytes, redis.rpoplpush_sync(INCOMING_TX_KEY, PROCESSING_TX_KEY, decode=False))
    if item is not None:
        if LEVEL != "1" and LEVEL != "5":
            if item_is_expired(item):
                redis.lpop_sync(PROCESSING_TX_KEY, decode=False)
                return get_next_item()

        next_item = json.loads(item)
        _log.info(f"Next item: {next_item}")
        return next_item

    return None


def get_new_transactions() -> List[transaction_model.TransactionModel]:
    """Get all new transactions from the incoming queue"""
    if LEVEL != "1":
        raise RuntimeError("Getting transactions is a level 1 action")

    transactions = []
    # Only allow up to 1000 transactions to process at a time
    length = min(redis.llen_sync(INCOMING_TX_KEY), 10000)
    p = redis.pipeline_sync()
    for _ in range(0, length):
        p.rpoplpush(INCOMING_TX_KEY, PROCESSING_TX_KEY)
    txn = p.execute()
    for string in txn:
        dictionary = json.loads(string)
        txn_model = transaction_model.new_from_queue_input(dictionary)
        transactions.append(txn_model)
    return transactions


def get_next_l1_block() -> Optional[l1_block_model.L1BlockModel]:
    """Get (and pop) the next l1 block to process off the queue"""
    if LEVEL != "2":
        raise RuntimeError("Getting next l1 block from queue is a level 2 action")

    next_item = get_next_item()

    if not next_item:
        return None

    return l1_block_model.new_from_stripped_block(next_item)


def get_next_l2_blocks() -> Union[Tuple[None, None], Tuple["L1Headers", List[l2_block_model.L2BlockModel]]]:
    """Get (and pop) the next l2 queue array to process"""
    if LEVEL != "3":
        raise RuntimeError("Getting next l2 array from queue is a level 3 action")
    next_item = get_next_item()

    if not next_item:
        return (None, None)

    l2_blocks = []
    for block in next_item["l2-blocks"]:
        try:
            l2_blocks.append(l2_block_model.new_from_at_rest(block))
        except Exception:
            _log.exception("Error parsing an l2 block from input")
    l1_headers: "L1Headers" = {
        "dc_id": next_item["header"]["dc_id"],
        "block_id": next_item["header"]["block_id"],
        "proof": next_item["header"]["stripped_proof"],
    }
    return (l1_headers, l2_blocks)


def get_next_l3_block() -> Union[Tuple[None, None], Tuple["L1Headers", List[l3_block_model.L3BlockModel]]]:
    """Get (and pop) the next l3 block to process off the queue"""
    if LEVEL != "4":
        raise RuntimeError("Getting next l3 item from queue is a level 4 action")
    next_item = get_next_item()

    if not next_item:
        return (None, None)

    l3_blocks = []
    for block in next_item["l3-blocks"]:
        try:
            l3_blocks.append(l3_block_model.new_from_at_rest(block))
        except Exception:
            _log.exception("Error parsing an l3 block from input")
    l1_headers: "L1Headers" = {
        "dc_id": next_item["header"]["dc_id"],
        "block_id": next_item["header"]["block_id"],
        "proof": next_item["header"]["stripped_proof"],
    }
    return (l1_headers, l3_blocks)


def get_new_l4_blocks() -> List[bytes]:
    """Get all new l4 records from the incoming queue"""
    if LEVEL != "5":
        raise RuntimeError("Getting l4_blocks is a level 5 action")
    l4_blocks = []
    for _ in range(0, redis.llen_sync(INCOMING_TX_KEY)):
        # These are in lists because enterprise will be able to specify more than one l4.
        l4_blocks_list = cast(bytes, redis.rpoplpush_sync(INCOMING_TX_KEY, PROCESSING_TX_KEY, decode=False))
        l4_blocks.append(l4_blocks_list)
    return l4_blocks

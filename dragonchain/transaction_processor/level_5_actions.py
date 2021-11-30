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

import os
import time
import json
import math
import uuid
from typing import cast, Iterable, List, Dict, Union, Any, TYPE_CHECKING

import fastjsonschema

from dragonchain.lib.interfaces import storage
from dragonchain.lib.dto import schema
from dragonchain.lib.dto import l5_block_model
from dragonchain.lib import keys
from dragonchain.lib import broadcast
from dragonchain.lib import party
from dragonchain.lib import matchmaking
from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib.dao import interchain_dao
from dragonchain.lib import queue
from dragonchain.transaction_processor import shared_functions
from dragonchain.lib.database import elasticsearch
from dragonchain.lib.database import redis

FAILED_CLAIMS_KEY = "mq:failed-claims"

if TYPE_CHECKING:
    from dragonchain.lib.dto import model  # noqa: F401

PROOF_SCHEME = os.environ["PROOF_SCHEME"].lower()
ADDRESS = os.environ["INTERNAL_ID"]
WATCH_INTERVAL = 600  # Default: 10 minutes as seconds
TRANSACTION_BUFFER = 5  # The minimum number of transactions you are estimated to be able to send before no longer accepting blocks from lower nodes
# All of these will be defined by calling setup() before using the rest of the module, hence the casts
BROADCAST_INTERVAL = cast(int, None)
INTERCHAIN_NETWORK = cast(str, None)
FUNDED = cast(bool, None)
_interchain_client = cast("model.InterchainModel", None)

_log = logger.get_logger()
_validate_l4_block_at_rest = fastjsonschema.compile(schema.l4_block_at_rest_schema)


def setup() -> None:
    """
    This function must be called to set up module state before using the rest of the module
    This is stubbed like so to assist in testing
    """
    global BROADCAST_INTERVAL
    global INTERCHAIN_NETWORK
    global FUNDED
    global _interchain_client
    my_config = matchmaking.get_matchmaking_config()
    BROADCAST_INTERVAL = int(my_config["broadcastInterval"] * 3600)
    INTERCHAIN_NETWORK = my_config["network"]
    FUNDED = my_config["funded"]
    _interchain_client = interchain_dao.get_default_interchain_client()
    _log.info(f"[L5] MY CONFIG -------> {my_config}")


def execute() -> None:
    """
    * Pops Level 4 records off the queue and Sets them to storage in directory called toBroadcast-${block_id}
    * Publishes to public nodes when required
    * Locates confirmations from public nodes when required
    * Sends receipts to all L1 blocks represented in public broadcast
    * Finalizes any previously failed claims present in backlog
    """
    matchmaking.renew_registration_if_necessary()
    # Check if there are any funds
    if has_funds_for_transactions():
        _log.info("[L5] Has funds, proceeding")
        # Get the block number for the pending L5
        current_block_id = str(int(get_last_block_number()) + 1)

        # Verify the blocks and add to storage pool where they wait to be broadcasted
        store_l4_blocks(current_block_id)

        # Create and Send L5 block to public blockchain
        if should_broadcast(current_block_id):
            # TODO: if any of these steps fail, we need to roll back or retry
            l5_block = create_l5_block(current_block_id)
            broadcast_to_public_chain(l5_block)
            broadcast_clean_up(l5_block)
            # Check to see if any more funds have been added to wallet
            watch_for_funds()
    else:
        # 20 minute timer watcher
        _log.info("[L5] No funds, checking if time to watch")
        if is_time_to_watch():
            # Check to see if any funds have been added to wallet
            watch_for_funds()

    # Only check confirmations if there are any pending
    check_confirmations()

    # go through the failed claims backlog
    _log.info("Trying to finalize any previously failed claims...")
    process_claims_backlog()


def process_claims_backlog() -> None:
    claims_set = redis.smembers_sync(FAILED_CLAIMS_KEY)  # used sadd to make a set
    _log.info(f"Claim backlog count: {len(claims_set)}")
    for claim_check_id in claims_set:
        try:
            matchmaking.resolve_claim_check(claim_check_id)
        except exceptions.NotFound:
            # If claim is not found, then this claim is irrelevant and we can safely skip
            pass
        except Exception:
            _log.exception("Failure to finalize claim in matchmaking.  Skipping the rest of the retry queue.")
            return  # short-circuit and exit early, matchmaking still unreachable
        redis.srem_sync(FAILED_CLAIMS_KEY, claim_check_id)  # claim successfully finalized, remove from backlog


def broadcast_clean_up(l5_block: l5_block_model.L5BlockModel) -> None:
    # remove block form awaiting broadcast
    _log.info(f"[L5] Deleting block from to broadcast blockid: {l5_block.block_id}")
    storage.delete_directory(f"BROADCAST/TO_BROADCAST/{l5_block.block_id}")

    # Set last block number and last broadcast time
    set_last_block_number(l5_block.block_id)

    set_last_broadcast_time()


def store_l4_blocks(next_block_id_to_broadcast: str) -> None:
    # Gets stringified lists of L4 blocks from different L1s
    # Shape: ["{l4 block in transit}", "{l4 block in transit}"]
    _log.info("[L5] Storing L4 blocks")
    queue.check_and_recover_processing_if_necessary()
    l4_blocks = queue.get_new_l4_blocks()
    _log.info(f"[L5] Popped {len(l4_blocks)} L4 blocks off of queue")
    if l4_blocks:
        verified_records = verify_blocks(l4_blocks)
        storage.put_object_as_json(f"BROADCAST/TO_BROADCAST/{next_block_id_to_broadcast}/{str(uuid.uuid4())}", verified_records)
    # Successfully handled block popped from redis
    queue.clear_processing_queue()


def verify_blocks(l4_blocks: Iterable[bytes]) -> List[Dict[str, Any]]:
    verified_records = []
    for l4_blocks_in_transit in l4_blocks:
        # For each record, validate or mark as invalid
        for record in json.loads(l4_blocks_in_transit)["l4-blocks"]:
            verified_records.append(verify_block(record))

    return verified_records


def verify_block(l4_block: Dict[str, Any]) -> Dict[str, Any]:
    try:
        _validate_l4_block_at_rest(l4_block)
    except fastjsonschema.JsonSchemaException:
        _log.exception(f"[L5] [MALFORMED_BLOCK]: Tagging record invalid. {l4_block}")
        l4_block["is_invalid"] = True

    return l4_block


def broadcast_to_public_chain(l5_block: l5_block_model.L5BlockModel) -> None:
    _log.info("[L5] Preparing to broadcast")
    # Hash the block and publish the block to a public network
    public_hash = keys.get_my_keys().hash_l5_for_public_broadcast(l5_block)
    transaction_hash = _interchain_client.publish_l5_hash_to_public_network(public_hash)
    _log.info("[L5] After Publish to public network, setting new broadcast time")
    _log.info(f"[L5] transaction_hash {transaction_hash}")

    # Append transaction hash to list, add network and last block sent at
    l5_block.transaction_hash += [transaction_hash]
    l5_block.block_last_sent_at = _interchain_client.get_current_block()
    l5_block.network = INTERCHAIN_NETWORK

    storage_key = f"BLOCK/{l5_block.block_id}"
    _log.info(f"[L5] Adding to storage at {storage_key} and creating index")
    storage.put_object_as_json(storage_key, l5_block.export_as_at_rest())
    if elasticsearch.ENABLED:
        elasticsearch.put_document(elasticsearch.Indexes.block.value, l5_block.export_as_search_index(),
                                   l5_block.block_id)


def check_confirmations() -> None:
    last_confirmed_block = get_last_confirmed_block()
    last_confirmed_block_number = last_confirmed_block["block_id"]
    last_created_block = get_last_block_number()

    _log.info(f"[L5] Last confirmed block is {last_confirmed_block_number}, last created block is {last_created_block}")

    if int(last_confirmed_block_number) < int(last_created_block):
        # Check for confirmations
        next_block_to_confirm = int(last_confirmed_block_number) + 1
        block_key = f"BLOCK/{next_block_to_confirm}"
        block = l5_block_model.new_from_at_rest(storage.get_json_from_object(block_key))

        for txn_hash in block.transaction_hash:
            try:
                if _interchain_client.is_transaction_confirmed(txn_hash):
                    finalize_block(block, last_confirmed_block, txn_hash)
                    # Stop execution here!
                    return
            except exceptions.TransactionNotFound:
                #  If transaction not found, it may have been dropped, so we remove it from the block
                block.transaction_hash.remove(txn_hash)

        # If execution did not stop, the block is not confirmed.
        if _interchain_client.should_retry_broadcast(block.block_last_sent_at):
            broadcast_to_public_chain(block)


def finalize_block(block: l5_block_model.L5BlockModel, last_confirmed_block: Dict[str, Any], confirmed_txn_hash: str) -> None:
    _log.info(f"[L5] Block {block.block_id} confirmed")
    if last_confirmed_block["proof"].get("proof"):
        block.prev_proof = last_confirmed_block["proof"]["proof"]

    _log.info("[L5] Signing block")
    block.transaction_hash = [confirmed_txn_hash]
    block.proof = keys.get_my_keys().sign_block(block)

    _log.info("[L5] Storing new block and moving pointers")
    storage.put_object_as_json(f"BLOCK/{block.block_id}", block.export_as_at_rest())
    # In the future if we change/add indexes to an L5 block, it may need to be re-indexed here.
    # For now, no re-indexing is necessary, only a storage update
    set_last_confirmed_block(block)

    # Notify L1s that contributed to L5 block
    broadcast.dispatch(block)


def get_last_block_number() -> str:
    try:
        return storage.get("BROADCAST/LAST_BLOCK").decode("utf-8")
    except exceptions.NotFound:
        shared_functions.sanity_check_empty_chain()
        return "0"


def get_last_confirmed_block() -> Dict[str, Any]:
    try:
        return storage.get_json_from_object("BROADCAST/LAST_CONFIRMED_BLOCK")
    except exceptions.NotFound:
        return {"block_id": "0", "proof": {}}


def set_last_block_number(block_id: str) -> None:
    storage.put("BROADCAST/LAST_BLOCK", block_id.encode("utf-8"))


def set_last_confirmed_block(l5_block: l5_block_model.L5BlockModel) -> None:
    storage.put_object_as_json("BROADCAST/LAST_CONFIRMED_BLOCK", {"block_id": l5_block.block_id, "proof": l5_block.export_as_at_rest()["proof"]})


def get_last_broadcast_time() -> int:
    last_broadcast_time = storage.get("BROADCAST/LAST_BROADCAST_TIME").decode("utf-8")
    return int(last_broadcast_time)


def get_last_watch_time() -> int:
    last_watch_time = storage.get("BROADCAST/LAST_WATCH_TIME").decode("utf-8")
    return int(last_watch_time)


def set_last_broadcast_time() -> None:
    storage.put("BROADCAST/LAST_BROADCAST_TIME", str(int(time.time())).encode("utf-8"))


def set_last_watch_time() -> None:
    storage.put("BROADCAST/LAST_WATCH_TIME", str(int(time.time())).encode("utf-8"))


def set_funds(balance: Union[str, int, float]) -> None:
    storage.put("BROADCAST/CURRENT_FUNDS", str(balance).encode("utf-8"))


def should_broadcast(current_block_id: str) -> bool:
    try:
        last_broadcast_time = get_last_broadcast_time()
        _log.info(f"[L5] Broadcast time: {last_broadcast_time}")
    except exceptions.NotFound:
        _log.info("[L5] Last broadcast time not found, calling set")
        set_last_broadcast_time()
        return False

    current_time = int(time.time())
    time_since_last_broadcast = current_time - last_broadcast_time

    if time_since_last_broadcast > BROADCAST_INTERVAL:
        _log.info("[L5] It is time to broadcast!")
        if is_backlog(current_block_id):
            return True

        _log.info("[L5] There were no transactions.")
        set_last_broadcast_time()

    _log.info(f"[L5] Time to next broadcast: {BROADCAST_INTERVAL - time_since_last_broadcast} seconds")
    return False


def is_time_to_watch() -> bool:
    try:
        last_watch_time = get_last_watch_time()
        _log.info(last_watch_time)
    except exceptions.NotFound:
        _log.info("[L5] Last watch time not set. Setting for first time...")
        set_last_watch_time()
        return True

    current_time = int(time.time())
    time_since_last_watch = current_time - last_watch_time
    if time_since_last_watch > WATCH_INTERVAL:
        _log.info("[L5] It is time to watch!")
        return True

    _log.info(f"[L5] Time to next watch: {WATCH_INTERVAL - time_since_last_watch} seconds")
    return False


def watch_for_funds() -> None:
    _log.info("[L5] Watching for funds")
    current_funds = _interchain_client.check_balance()
    _log.info(f"[L5] raw balance: {current_funds}")

    set_funds(current_funds)
    set_last_watch_time()

    estimated_transaction_fee = _interchain_client.get_transaction_fee_estimate()

    global FUNDED
    _log.info("[L5] Checking if should update funded flag...")
    _log.info(
        f"[L5] Funded: {FUNDED}\tEstimated Fee: {estimated_transaction_fee}\tTransaction Buffer: {TRANSACTION_BUFFER}\tCurrent Funds: {current_funds}"
    )
    if not FUNDED and (estimated_transaction_fee * TRANSACTION_BUFFER) < current_funds:
        _log.info("[L5] Updating metadata!")
        matchmaking.update_funded_flag(True)
        FUNDED = True


def has_funds_for_transactions() -> bool:
    try:
        current_funds = float(storage.get("BROADCAST/CURRENT_FUNDS").decode("utf-8"))
        estimated_transaction_fee = _interchain_client.get_transaction_fee_estimate()

        if (estimated_transaction_fee * TRANSACTION_BUFFER) < current_funds:
            _log.info("[L5] You have enough funds!")
            return True
        else:
            global FUNDED
            if FUNDED:
                _log.info("[L5] Low on funds, deregistering node from matchmaking")
                matchmaking.update_funded_flag(False)
                FUNDED = False
            return False
    except exceptions.NotFound:
        return False


def is_backlog(current_block_id: str) -> bool:
    return storage.does_superkey_exist(f"BROADCAST/TO_BROADCAST/{current_block_id}/")


def create_l5_block(block_id: str) -> l5_block_model.L5BlockModel:
    """
    Creates unfinalized L5 block that needs confirmation
    """
    l5_block = l5_block_model.L5BlockModel(
        dc_id=keys.get_public_id(),
        current_ddss=party.get_address_ddss(ADDRESS),  # Get DDSS from party, cached hourly
        block_id=str(block_id),
        timestamp=str(math.floor(time.time())),
        prev_proof="",
        scheme=PROOF_SCHEME,
        l4_blocks=get_pending_l4_blocks(block_id),
    )

    return l5_block


def get_pending_l4_blocks(block_id: str) -> List[str]:
    all_waiting_verification_keys = storage.list_objects(f"BROADCAST/TO_BROADCAST/{block_id}")

    l4_blocks = []
    for key in all_waiting_verification_keys:
        record_list = storage.get_json_from_object(key)

        for record in record_list:
            item = {
                "l1_dc_id": record["header"]["l1_dc_id"],
                "l1_block_id": record["header"]["l1_block_id"],
                "l4_dc_id": record["header"]["dc_id"],
                "l4_block_id": record["header"]["block_id"],
                "l4_proof": record["proof"]["proof"],
            }
            if record.get("is_invalid"):
                item["is_invalid"] = record.get("is_invalid")
            l4_blocks.append(json.dumps(item, separators=(",", ":")))

    return l4_blocks

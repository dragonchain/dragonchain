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
import time
import math
import json
from typing import Dict, Tuple, Optional, Any, TYPE_CHECKING

from dragonchain.lib import broadcast
from dragonchain.lib import keys
from dragonchain.lib import matchmaking
from dragonchain.lib import party
from dragonchain.lib.dao import block_dao
from dragonchain.lib.dto import l2_block_model
from dragonchain.lib.dto import transaction_model
from dragonchain.transaction_processor import shared_functions
from dragonchain.lib import queue
from dragonchain import logger

if TYPE_CHECKING:
    from dragonchain.lib.dto import l1_block_model

PROOF_SCHEME = os.environ["PROOF_SCHEME"].lower()
ADDRESS = os.environ["INTERNAL_ID"]

_log = logger.get_logger()


def execute() -> None:
    """Gets the next L1 block from the queue and processes it"""
    matchmaking.renew_registration_if_necessary()
    t0 = time.time()
    l1_block = get_new_block()

    if l1_block:
        _log.info(f"[L2] Got next L1 block from dcid: {l1_block.dc_id} blockid: {l1_block.block_id}")
        t1 = time.time()

        if verify_transaction_count(l1_block.dc_id, l1_block.block_id, len(l1_block.stripped_transactions)):
            transaction_validation_map = process_transactions(l1_block)
            t2 = time.time()

            l2_block = create_block(l1_block, transaction_validation_map)
            t3 = time.time()

            send_data(l2_block)
            t4 = time.time()

            total = t4 - t0
            _log.info(f"[L2] Processed block {l2_block.l1_block_id} from {l2_block.l1_dc_id} in {total:.4f} seconds")
            _log.info(f"[L2] Retrieving L1 block from queue: {t1 - t0:.4f} sec ({((t1 - t0) / total) * 100:.1f}% of processing)")
            _log.info(f"[L2] Processing transactions: {t2 - t1:.4f} sec ({((t2 - t1) / total) * 100:.1f}% of processing)")
            _log.info(f"[L2] Creating L2 block: {t3 - t2:.4f} sec ({((t3 - t2) / total) * 100:.1f}% of processing)")
            _log.info(f"[L2] Uploading block and broadcasting down: {t4 - t3:.4f} sec ({((t4 - t3) / total) * 100:.1f}% of processing)")

        # Clear our processing queue (finished successfully)
        clear_processing_block()
        recurse_if_necessary()


def clear_processing_block() -> None:
    queue.clear_processing_queue()


def get_new_block() -> Optional["l1_block_model.L1BlockModel"]:
    # Safety check to recover after unexpected crash while creating last block if necessary
    queue.check_and_recover_processing_if_necessary()
    return queue.get_next_l1_block()


def get_verifying_keys(chain_id: str) -> keys.DCKeys:
    _log.info("[L2] Getting L1's verifying keys")
    return keys.DCKeys(chain_id)


def verify_block(block: "l1_block_model.L1BlockModel", keys: keys.DCKeys) -> bool:
    _log.info("[L2] Verifying whole block signature")
    return keys.verify_block(block)


def send_data(block: l2_block_model.L2BlockModel) -> None:
    _log.info("[L2] Uploading block")
    block_dao.insert_block(block)

    _log.info("[L2] Inserting complete. Broadcasting block")
    broadcast.dispatch(block)


def process_transactions(l1_block: "l1_block_model.L1BlockModel") -> Dict[str, bool]:
    txn_map: Dict[str, bool] = {}
    try:
        verify_keys = get_verifying_keys(l1_block.dc_id)
        if verify_block(l1_block, verify_keys):
            verify_transactions(l1_block, verify_keys, txn_map)
        else:
            mark_invalid(l1_block, txn_map)
    except Exception:
        mark_invalid(l1_block, txn_map)

    return txn_map


def verify_transactions(block: "l1_block_model.L1BlockModel", keys: keys.DCKeys, txn_map: Dict[str, Any]) -> None:
    _log.info("[L2] Whole block is valid, verifying individual transactions")
    for txn in block.stripped_transactions:
        try:
            txn = transaction_model.new_from_stripped_block_input(txn)
            valid = keys.verify_stripped_transaction(txn)
            _log.info(f"[L2] Txn id {txn.txn_id} evaluated with validation status: {valid}")
            txn_map[txn.txn_id] = valid
        except Exception:
            _log.exception(f"[L2] Couldn't parse/verify txn: {txn}")


def verify_transaction_count(l1_dc_id: str, block_id: str, txn_count: int) -> bool:
    claimed_txn_count = matchmaking.get_claimed_txn_count(l1_dc_id, block_id)
    if claimed_txn_count != txn_count:
        _log.warning(("Transaction count from claim doesn't match transaction count from matchmaking. " "Won't process this block"))
        return False
    return True


def mark_invalid(block: "l1_block_model.L1BlockModel", txn_map: Dict[str, Any]) -> None:
    _log.info("[L2] Whole block is invalid, invalidating all transactions")
    for txn in block.stripped_transactions:
        try:
            txn = json.loads(txn)
            txn_map[txn["header"]["txn_id"]] = False
        except Exception:
            _log.exception(f"[L2] Couldn't parse tx_id for tx: {txn}")


def create_block(l1_block: "l1_block_model.L1BlockModel", transaction_map: Dict[str, Any]) -> l2_block_model.L2BlockModel:
    block_id, prev_proof = get_next_block_info()

    l2_block = l2_block_model.L2BlockModel(
        dc_id=keys.get_public_id(),
        current_ddss=party.get_address_ddss(ADDRESS),  # Get DDSS from party, cached hourly
        block_id=str(block_id),
        timestamp=str(math.floor(time.time())),
        prev_proof=prev_proof,
        scheme=PROOF_SCHEME,
        l1_dc_id=l1_block.dc_id,
        l1_block_id=l1_block.block_id,
        l1_proof=l1_block.proof,
        validations_dict=transaction_map,
    )

    sign_block(l2_block)

    return l2_block


def get_next_block_info() -> Tuple[int, str]:
    _log.info("[L2] Creating L2 block")
    previous_proof_dict = block_dao.get_last_block_proof()
    _log.info(f"[L2] Got previous block proof: {previous_proof_dict}")

    if not previous_proof_dict:
        # Throws an exception if sanity check fails
        shared_functions.sanity_check_empty_chain()
        block_id = 1
        prev_proof = ""
    else:
        block_id = int(previous_proof_dict["block_id"]) + 1
        prev_proof = previous_proof_dict["proof"]
        _log.info(f"[L2] Got previous block id, incremented current block id to {block_id}")

    return block_id, prev_proof


def sign_block(l2_block: l2_block_model.L2BlockModel) -> None:
    if PROOF_SCHEME == "work":
        _log.info("[L2] Performing PoW on block")
        l2_block.proof, l2_block.nonce = keys.get_my_keys().pow_block(l2_block)
    else:
        _log.info("[L2] Signing block")
        l2_block.proof = keys.get_my_keys().sign_block(l2_block)


def recurse_if_necessary() -> None:
    if queue.is_not_empty():
        _log.info("[L2] Another block is queue, immediately starting processing")
        execute()
    else:
        _log.info("[L2] Block processing complete and no new block to process. Waiting")

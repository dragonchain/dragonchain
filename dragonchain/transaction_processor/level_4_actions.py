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
import math
from typing import Set, Dict, List, Union, Tuple, Any, TYPE_CHECKING

from dragonchain.lib.dao import block_dao
from dragonchain.lib.dto import l4_block_model
from dragonchain.lib import matchmaking
from dragonchain.lib import broadcast
from dragonchain.lib import keys
from dragonchain.lib import party
from dragonchain.lib import queue
from dragonchain import logger
from dragonchain.transaction_processor import shared_functions

if TYPE_CHECKING:
    from dragonchain.lib.types import L1Headers
    from dragonchain.lib.dto import l3_block_model

PROOF_SCHEME = os.environ["PROOF_SCHEME"].lower()
ADDRESS = os.environ["INTERNAL_ID"]

_log = logger.get_logger()


def execute() -> None:
    """Gets the next L3 block content from the queue and processes it"""
    matchmaking.renew_registration_if_necessary()
    t0 = time.time()

    l1_headers, l3_blocks = get_new_blocks()
    if l3_blocks and l1_headers:
        _log.info(f"[L4] Got next L3 block array from dcid: {l1_headers['dc_id']} for blockid: {l1_headers['block_id']}")
        t1 = time.time()

        validations = verify_blocks(l3_blocks, l1_headers)
        t2 = time.time()

        l4_block = create_block(l1_headers, validations)
        t3 = time.time()

        send_data(l4_block)
        t4 = time.time()

        # Clear our processing queue (finished successfully)
        clear_processing_blocks()

        total = t4 - t0
        _log.info(f"[L4] Processed block l3 blocks in {total:.4f} seconds")
        _log.info(f"[L4] Retrieving L3 block from queue: {t1 - t0:.4f} sec ({((t1 - t0) / total) * 100:.1f}% of processing)")
        _log.info(f"[L4] Validating all L3 block proofs: {t2 - t1:.4f} sec ({((t2 - t1) / total) * 100:.1f}% of processing)")
        _log.info(f"[L4] Creating block with proof: {t3 - t2:.4f} sec ({((t3 - t2) / total) * 100:.1f}% of processing)")
        _log.info(f"[L4] Uploading block and broadcasting down: {t4 - t3:.4f} sec ({((t4 - t3) / total) * 100:.1f}% of processing)")

        recurse_if_necessary()
    else:
        # Clear our processing queue
        clear_processing_blocks()

    if l1_headers is not None and l3_blocks is None:
        try:
            _log.warning(f"Bad Block received from lower level. L1 Headers: {l1_headers}")
        except Exception:  # nosec (We don't care if l1_headers is an error/not defined and this log fails)
            pass

        # Clear our processing queue
        clear_processing_blocks()


def clear_processing_blocks() -> None:
    queue.clear_processing_queue()


def get_new_blocks() -> Union[Tuple[None, None], Tuple["L1Headers", List["l3_block_model.L3BlockModel"]]]:
    # Safety check to recover after unexpected crash while creating last block if necessary
    queue.check_and_recover_processing_if_necessary()
    return queue.get_next_l3_block()


def send_data(block: l4_block_model.L4BlockModel) -> None:
    _log.info("[L4] Block created. Uploading data to storage")
    block_dao.insert_block(block)

    _log.info("[L4] Inserting complete. Broadcasting block")
    broadcast.dispatch(block)


def get_verifying_keys(chain_id: str) -> keys.DCKeys:
    return keys.DCKeys(chain_id)


def recurse_if_necessary() -> None:
    if queue.is_not_empty():
        _log.info("[L4] Another block is queue, immediately starting processing")
        execute()
    else:
        _log.info("[L4] Block processing complete and no new block to process. Waiting")


def verify_blocks(l3_blocks: List["l3_block_model.L3BlockModel"], l1_headers: "L1Headers") -> List[Dict[str, Any]]:
    validations = []
    checked: Set[str] = set()
    for block in l3_blocks:
        # We use a checked array with proofs (which are unique) to make sure we don't process
        # a block twice, and ensure the block we're looking at is actually relevant
        check = (
            block.proof not in checked
            and block.l1_dc_id == l1_headers["dc_id"]
            and block.l1_block_id == l1_headers["block_id"]
            and block.l1_proof == l1_headers["proof"]
        )

        if check:
            validations.append(verify_block(block))
        else:
            _log.info(f"[L4] L3 block was duplicated or not relevant to this verification.\nBlock in question: {block.__dict__}")
        # Finally, add this block into our checked blocks list
        checked.add(block.proof)

    return validations


def verify_block(block: "l3_block_model.L3BlockModel") -> Dict[str, Any]:
    try:
        verify_keys = get_verifying_keys(block.dc_id)
        _log.info(f"[L4] Verifying proof for L2 block id {block.block_id} from {block.dc_id}")
        if verify_keys.verify_block(block):
            verification = True
            _log.info(f"[L4] Finished processing valid L3 block {block.block_id}")
        else:
            verification = False
            _log.info(f"[L4] Proof for L3 block id {block.block_id} from {block.dc_id} was invalid")
    except Exception:
        _log.exception("[L4] Could not get L3 chain's verifying keys. Marking block as invalid.")
        verification = False
    return {"l3_dc_id": block.dc_id, "l3_block_id": block.block_id, "l3_proof": block.proof, "valid": verification}


def create_block(l1_headers: "L1Headers", validations: List[Dict[str, Any]]) -> l4_block_model.L4BlockModel:
    block_id, prev_proof = get_next_block_info()

    l4_block = l4_block_model.L4BlockModel(
        dc_id=keys.get_public_id(),
        current_ddss=party.get_address_ddss(ADDRESS),  # Get DDSS from party, cached hourly
        block_id=str(block_id),
        timestamp=str(math.floor(time.time())),
        prev_proof=prev_proof,
        scheme=PROOF_SCHEME,
        l1_dc_id=l1_headers["dc_id"],
        l1_block_id=l1_headers["block_id"],
        l1_proof=l1_headers["proof"],
        validations=validations,
    )

    sign_block(l4_block)

    return l4_block


def get_next_block_info() -> Tuple[int, str]:
    previous = block_dao.get_last_block_proof()
    _log.info(f"[L4] Got previous block information: {previous}")
    if not previous:
        # Throws an exception if sanity check fails
        shared_functions.sanity_check_empty_chain()
        block_id = 1
        prev_proof = ""
    else:
        block_id = int(previous["block_id"]) + 1
        prev_proof = previous["proof"]
        _log.info(f"[L4] Got previous block id, incremented current block id to {block_id}")

    return block_id, prev_proof


def sign_block(l4_block: l4_block_model.L4BlockModel) -> None:
    if PROOF_SCHEME == "work":
        _log.info("[L4] Performing PoW on block")
        l4_block.proof, l4_block.nonce = keys.get_my_keys().pow_block(l4_block)
    else:
        _log.info("[L4] Signing block")
        l4_block.proof = keys.get_my_keys().sign_block(l4_block)
    _log.info(f"[L4] Finished Block:\n{l4_block.export_as_at_rest()}")

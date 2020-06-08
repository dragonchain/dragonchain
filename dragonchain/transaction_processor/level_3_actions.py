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
from typing import Set, Union, Tuple, List, Iterable, TYPE_CHECKING, Optional

from dragonchain.lib.dao import block_dao
from dragonchain.lib.dto import l3_block_model
from dragonchain.lib import keys
from dragonchain.lib import broadcast
from dragonchain.lib import matchmaking
from dragonchain.lib import party
from dragonchain.lib import queue
from dragonchain import logger, exceptions
from dragonchain.transaction_processor import shared_functions

if TYPE_CHECKING:
    from dragonchain.lib.dto import l2_block_model
    from dragonchain.lib.types import L1Headers


PROOF_SCHEME = os.environ["PROOF_SCHEME"].lower()
ADDRESS = os.environ["INTERNAL_ID"]

_log = logger.get_logger()


def execute() -> None:
    """Gets the next L2 block arrays from the queue and processes it"""
    matchmaking.renew_registration_if_necessary()
    t0 = time.time()

    l1_headers, l2_blocks = get_new_blocks()
    if l1_headers and l2_blocks:
        t1 = time.time()
        _log.info(f"[L3] Got next L2 block array from dcid: {l1_headers['dc_id']} blockid: {l1_headers['block_id']}")

        ddss, valid_block_count, regions, clouds = verify_blocks(l2_blocks, l1_headers)
        if not valid_block_count:
            _log.info("[L3] None of the L2 blocks sent up were valid. Not creating any block/verifications")
            clear_processing_blocks()
            recurse_if_necessary()
            return
        t2 = time.time()

        l3_block = create_block(l1_headers, ddss, valid_block_count, regions, clouds, l2_blocks)
        t3 = time.time()

        send_data(l3_block)
        t4 = time.time()

        # Clear our processing queue (finished successfully)
        clear_processing_blocks()

        total = t4 - t0
        _log.info(
            f"[L3] Processed {len(l2_blocks)} l2 blocks for l1 block id {l1_headers['dc_id']} with dcid {l1_headers['block_id']} in {total:.4f} seconds"
        )
        _log.info(f"[L3] Retrieving L2 block list from queue: {t1 - t0:.4f} sec ({((t1 - t0) / total) * 100:.1f}% of processing)")
        _log.info(f"[L3] Verified all L2 blocks in list: {t2 - t1:.4f} sec ({((t2 - t1) / total) * 100:.1f}% of processing)")
        _log.info(f"[L3] Creating block with proof: {t3 - t2:.4f} sec ({((t3 - t2) / total) * 100:.1f}% of processing)")
        _log.info(f"[L3] Uploading block and broadcasting down: {t4 - t3:.4f} sec ({((t4 - t3) / total) * 100:.1f}% of processing)")

        recurse_if_necessary()


def clear_processing_blocks() -> None:
    queue.clear_processing_queue()


def send_data(block: l3_block_model.L3BlockModel) -> None:
    _log.info("[L3] Uploading block")
    block_dao.insert_block(block)

    _log.info("[L3] Inserting complete. Broadcasting block")
    broadcast.dispatch(block)


def recurse_if_necessary() -> None:
    if queue.is_not_empty():
        _log.info("[L3] Another block is queue, immediately starting processing")
        execute()
    else:
        _log.info("[L3] Block processing complete and no new block to process. Waiting")


def get_new_blocks() -> Union[Tuple[None, None], Tuple["L1Headers", List["l2_block_model.L2BlockModel"]]]:
    # Safety check to recover after unexpected crash while creating last block if necessary
    queue.check_and_recover_processing_if_necessary()
    return queue.get_next_l2_blocks()


def get_verifying_keys(chain_id: str, override_level: Optional[str] = None) -> keys.DCKeys:
    return keys.DCKeys(chain_id, override_level=override_level)


def verify_blocks(l2_blocks: Iterable["l2_block_model.L2BlockModel"], l1_headers: "L1Headers") -> Tuple[int, int, List[str], List[str]]:
    ddss = 0
    l2_count = 0
    regions: Set[str] = set()
    clouds: Set[str] = set()
    checked: Set[str] = set()
    for block in l2_blocks:
        # We use a checked array with proofs (which are unique) to make sure we don't process
        # a block twice, and ensures the block we're looking at is actually relevant
        check = (
            block.proof not in checked
            and block.l1_dc_id == l1_headers["dc_id"]
            and block.l1_block_id == l1_headers["block_id"]
            and block.l1_proof == l1_headers["proof"]
        )

        if check:
            clouds, regions, ddss, l2_count = verify_block(block, clouds, regions, ddss, l2_count)
        else:
            _log.info(f"[L3] L2 block was duplicated or not relevant to this verification.\n{block.__dict__}")

        # Finally, add this block into our checked blocks list
        checked.add(block.proof)

    return ddss, l2_count, list(regions), list(clouds)


def verify_block(
    block: "l2_block_model.L2BlockModel", clouds: Set[str], regions: Set[str], ddss: int, l2_count: int
) -> Tuple[Set[str], Set[str], int, int]:
    try:
        l2_verify_keys = get_verifying_keys(block.dc_id, "2")
        _log.info(f"[L3] Verifying proof for L2 block id {block.block_id} from {block.dc_id}")
        if l2_verify_keys.verify_block(block):
            l2_count += 1
            l2_ddss = block.current_ddss or "0"
            try:
                matchmaking_config = matchmaking.get_registration(block.dc_id)
                clouds.add(matchmaking_config["cloud"])
                regions.add(matchmaking_config["region"])
            except exceptions.NotFound:
                _log.info("Unable to pull matchmaking record for this block")
                pass
            ddss += int(float(l2_ddss))
            _log.info(f"[L3] Finished processing valid L2 block {block.block_id}")
        else:
            _log.info(f"[L3] Proof for L2 block id {block.block_id} from {block.dc_id} was invalid. Not including block in stats.")
    except Exception:
        _log.exception("[L3] Could not get L2's verifying keys. Not incrementing stats for this block.")

    return clouds, regions, ddss, l2_count


def get_next_block_info() -> Tuple[int, str]:
    previous = block_dao.get_last_block_proof()
    _log.info(f"[L3] Got previous block information: {previous}")
    if not previous:
        # Throws an exception if sanity check fails
        shared_functions.sanity_check_empty_chain()
        block_id = 1
        prev_proof = ""
    else:
        block_id = int(previous["block_id"]) + 1
        prev_proof = previous["proof"]

    _log.info(f"[L3] Block ID: {block_id}")

    return block_id, prev_proof


def create_block(
    l1_headers: "L1Headers",
    ddss: Union[str, float, int],
    valid_block_count: int,
    regions: List[str],
    clouds: List[str],
    l2_blocks: Iterable["l2_block_model.L2BlockModel"],
) -> l3_block_model.L3BlockModel:
    block_id, prev_proof = get_next_block_info()

    # Pull configuration from matchmaking directly to get DDSS (not stored locally)
    l2_proofs = []
    for block in l2_blocks:
        l2_proofs.append({"dc_id": block.dc_id, "block_id": block.block_id, "proof": block.proof})

    l3_block = l3_block_model.L3BlockModel(
        dc_id=keys.get_public_id(),
        current_ddss=party.get_address_ddss(ADDRESS),  # Get DDSS from party, cached hourly
        block_id=str(block_id),
        timestamp=str(math.floor(time.time())),
        prev_proof=prev_proof,
        scheme=PROOF_SCHEME,
        l1_dc_id=l1_headers["dc_id"],
        l1_block_id=l1_headers["block_id"],
        l1_proof=l1_headers["proof"],
        l2_proofs=l2_proofs,
        ddss=str(ddss),
        l2_count=str(valid_block_count),
        regions=regions,
        clouds=clouds,
    )

    sign_block(l3_block)

    return l3_block


def sign_block(l3_block: l3_block_model.L3BlockModel) -> None:
    if PROOF_SCHEME == "work":
        _log.info("[L3] Performing PoW on block")
        l3_block.proof, l3_block.nonce = keys.get_my_keys().pow_block(l3_block)
    else:
        _log.info("[L3] Signing block")
        l3_block.proof = keys.get_my_keys().sign_block(l3_block)
    _log.info(f"[L3] Finished Block:\n{l3_block.export_as_at_rest()}")

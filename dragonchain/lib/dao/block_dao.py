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

from typing import List, Dict, Any, TYPE_CHECKING

from dragonchain.lib.dto import l1_block_model
from dragonchain.lib.dto import l2_block_model
from dragonchain.lib.dto import l3_block_model
from dragonchain.lib.dto import l4_block_model
from dragonchain.lib import dragonnet_config
from dragonchain.lib.interfaces import storage
from dragonchain.broadcast_processor import broadcast_functions
from dragonchain.lib.database import redisearch
from dragonchain import exceptions
from dragonchain import logger

if TYPE_CHECKING:
    from dragonchain.lib.dto import model

FOLDER = "BLOCK"
LAST_CLOSED_KEY = "LAST_BLOCK_PROOF"

_log = logger.get_logger()


def get_verifications_for_l1_block(block_id: str, level: int) -> List[Dict[str, Any]]:
    try:
        keys = list(broadcast_functions.get_receieved_verifications_for_block_and_level_sync(block_id, level))
        if len(keys) != 0:
            for i in range(len(keys)):
                keys[i] = f"{FOLDER}/{block_id}-l{level}-{keys[i]}"
            return [storage.get_json_from_object(x) for x in keys]
    except Exception:
        _log.exception("Error getting verifications from cached list. Falling back to direct storage list")
    # Only fall back to listing from storage if we don't have verifications already saved in redis
    prefix = f"{FOLDER}/{block_id}-l{level}"
    keys = storage.list_objects(prefix)
    _log.info(f"Verification keys by prefix {prefix}: {keys}")
    return [] if len(keys) == 0 else [storage.get_json_from_object(key) for key in keys]


def get_broadcast_dto(higher_level: int, block_id: str) -> Dict[str, Any]:
    """Get the broadcast dto for a block to a certain level
    Args:
        higher_level: (2-5)
        block_id: block_id used to locate block in storage
    Returns:
        Broadcast DTO of requested
    """
    l1_block = storage.get_json_from_object(f"{FOLDER}/{block_id}")
    if higher_level == 2:
        return l1_block_model.export_broadcast_dto(l1_block)
    else:
        required_verification_count = dragonnet_config.DRAGONNET_CONFIG[f"l{higher_level - 1}"]["nodesRequired"]
        verification_blocks = get_verifications_for_l1_block(block_id, (higher_level - 1))
        if len(verification_blocks) < required_verification_count:
            raise exceptions.NotEnoughVerifications(
                f"This chain requires {required_verification_count} level {higher_level - 1} verifications, but only {len(verification_blocks)} were found. (Probably just need to wait)"  # noqa: B950
            )
        if higher_level == 3:
            return l2_block_model.export_broadcast_dto(verification_blocks, l1_block)
        elif higher_level == 4:
            return l3_block_model.export_broadcast_dto(verification_blocks, l1_block)
        elif higher_level == 5:
            return l4_block_model.export_broadcast_dto(verification_blocks)
        else:
            raise exceptions.InvalidNodeLevel(f"Level {higher_level} is not valid for getting a broadcast DTO (Only allowed 2-5)")


def get_last_block_proof() -> Dict[str, str]:
    """Return the last closed block's ID and hash
    Returns:
        Result of last closed block lookup (empty dictionary if not found)
    """
    try:
        return storage.get_json_from_object(f"{FOLDER}/{LAST_CLOSED_KEY}")
    except exceptions.NotFound:
        return {}


def insert_block(block: "model.BlockModel") -> None:
    """
    Insert new block into blockchain and ref to block's hash
    """
    #  Create ref to this block for the next block
    last_block_ref = {"block_id": block.block_id, "proof": block.proof}
    #  Upload stripped block
    if redisearch.ENABLED:
        redisearch.put_document(redisearch.Indexes.block.value, block.block_id, block.export_as_search_index(), upsert=True)
    storage.put_object_as_json(f"{FOLDER}/{block.block_id}", block.export_as_at_rest())

    #  Upload ref
    storage.put_object_as_json(f"{FOLDER}/{LAST_CLOSED_KEY}", last_block_ref)

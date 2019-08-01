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

import re
import time
from typing import List, Tuple, Set

from dragonchain.lib import dragonnet_config
from dragonchain.lib.interfaces import storage
from dragonchain.lib.database import redis
from dragonchain import exceptions


IN_FLIGHT_KEY = "broadcast:in-flight"
BROADCAST_BLOCK_PREFIX = "broadcast:block"
CLAIM_CHECK_KEY = "broadcast:claimcheck"
FAULT_TOLERATION = 10  # Number of times fetching verifications fails before rolling back block verification state


def state_key(block_id: str) -> str:
    """Get the redis key for the state (current accepting level) of a block
    Args:
        block_id: block_id for the desired key
    Returns:
        Redis key for the broadcast state of the block_id
    """
    return f"{BROADCAST_BLOCK_PREFIX}:{block_id}:state"


def verifications_key(block_id: str, level: int) -> str:
    """Get the redis key for verifications of a certain level of a block
    Args:
        block_id: block_id for the desired key
        level: level for the verification list of a block
    Returns:
        Redis key for the broadcast state of the block_id
    """
    return f"{BROADCAST_BLOCK_PREFIX}:{block_id}:l{level}"


def storage_error_key(block_id: str) -> str:
    """Get the redis key for number of storage errors for block verifications
    Args:
        block_id: block_id for the desired key
    Returns:
        Redis key for the block storage errors
    """
    return f"{BROADCAST_BLOCK_PREFIX}:{block_id}:errors"


def increment_storage_error_sync(block_id: str, current_level: int) -> None:
    """When getting a storage error/inconsistency between redis/storage, this should be called
    This will roll-back a block to a previous level for verifications if FAULT_TOLERATION is surpassed for a block

    Basically, the state in redis can be a mis-representation of what's in actual storage, and if this occurs, we need to roll back
    the block verifications state and remove any bogus verifications from redis that aren't truly saved in storage, which happens on occasion
    Args:
        block_id: the block_id to increment a storage error
        current_level: the current block verification level state (should be in broadcast:block:state)
    """
    # Don't do anything if at or below level two because no verifications are required yet
    if current_level <= 2:
        return
    error_key = storage_error_key(block_id)
    current_count = int(redis.get_sync(error_key, decode=False) or 0)
    if current_count < FAULT_TOLERATION:
        redis.set_sync(error_key, str(current_count + 1))
        return
    # Beyond fault toleration, we must rollback this block

    # First find all verifications actually in storage
    prefix = f"BLOCK/{block_id}-l{current_level - 1}"
    good_verifications = set()
    for key in storage.list_objects(prefix):
        good_verifications.add(re.search(f"^{prefix}-(.*)", key).group(1))  # noqa: T484

    # Now find all verifications the system thinks we have in redis
    redis_verifications_key = verifications_key(block_id, current_level - 1)
    all_verifications = redis.smembers_sync(redis_verifications_key)

    # Remove all bad verifications recorded in redis that aren't in storage, and demote block to previous level
    p = redis.pipeline_sync()
    p.srem(redis_verifications_key, *all_verifications.difference(good_verifications))
    p.delete(error_key)
    p.set(state_key(block_id), str(current_level - 1))
    p.execute()


async def get_blocks_to_process_for_broadcast_async() -> List[Tuple[str, int]]:
    """Get the blocks scheduled to be checked by the broadcast processor right now
    Args:
    Returns:
        List of (block_id, score) tuples to be processed by the broadcast processor (limit of 1000)
    """
    return await redis.z_range_by_score_async(IN_FLIGHT_KEY, 0, int(time.time()), withscores=True, offset=0, count=1000)


async def get_current_block_level_async(block_id: str) -> int:
    """Get the current level of verifications that a particular block is accepting right now (async)
    Args:
        block_id: block_id to fetch the current level
    Returns:
        Int of the level of verifications that this block is accepting
    """
    return int(await redis.get_async(state_key(block_id), decode=False) or -1)


def get_current_block_level_sync(block_id: str) -> int:
    """Get the current level of verifications that a particular block is accepting right now (sync)
    Args:
        block_id: block_id to fetch the current level
    Returns:
        Int of the level of verifications that this block is accepting
    """
    return int(redis.get_sync(state_key(block_id), decode=False) or -1)


def is_block_accepting_verifications_from_level(block_id: str, level: int) -> bool:
    """Check if a block is currently accepting verifications from a particular level (sync)
    Args:
        block_id: block_id to fetch the current level
        level: verification level to check if accepting
    Returns:
        Boolean true if accepting, false if not
    """
    return get_current_block_level_sync(block_id) == level


async def set_current_block_level_async(block_id: str, level: int) -> None:
    """Set the current verification level for a block (async)
    Args:
        block_id: block_id to set
        level: verification level to set for block_id
    """
    await redis.set_async(state_key(block_id), str(level))


def set_current_block_level_sync(block_id: str, level: int) -> None:
    """Set the current verification level for a block (async)
    Args:
        block_id: block_id to set
        level: verification level to set for block_id
    """
    redis.set_sync(state_key(block_id), str(level))


def schedule_block_for_broadcast_sync(block_id: str, time: int = 0) -> None:
    """Schedule a certain block to be checked by the broadcast processor (sync)
    Args:
        block_id: block_id to schedule
        time: unix timestamp to re-schedule for checking (0 means ASAP)
    """
    redis.zadd_sync(IN_FLIGHT_KEY, {block_id: time})


async def schedule_block_for_broadcast_async(block_id: str, time: int = 0) -> None:
    """Schedule a certain block to be checked by the broadcast processor (sync)
    Args:
        block_id: block_id to schedule
        time: unix timestamp to re-schedule for checking (0 means ASAP)
    """
    await redis.zadd_async(IN_FLIGHT_KEY, time, block_id)


def set_receieved_verification_for_block_from_chain_sync(block_id: str, level: int, chain_id: str) -> None:
    """Signify a successful receipt from a higher level node receipt for a certain block (sync)
    Args:
        block_id: block_id of lvl 1 block for received receipt
        level: level of the node from the higher level receipt
        chain_id: id of the higher level dragonchain receipt
    """
    # Check that this block is accepting verifications for the specified level
    accepting_verification_level = get_current_block_level_sync(block_id)
    if accepting_verification_level != level:
        raise exceptions.NotAcceptingVerifications(
            f"Block {block_id} is only accepting verifications for level {accepting_verification_level} (Not {level}) at the moment"
        )

    set_key = verifications_key(block_id, level)
    p = redis.pipeline_sync()
    p.sadd(set_key, chain_id)
    p.scard(set_key)
    verifications = p.execute()[1]  # Execute the commands and get the result of the scard operation (number of members in the set)
    required = dragonnet_config.DRAGONNET_CONFIG[f"l{level}"]["nodesRequired"]

    # Check if this block needs to be promoted to the next level
    if verifications >= required:
        if level >= 5:
            # If level 5, block needs no more verifications; remove it from the broadcast system
            remove_block_from_broadcast_system_sync(block_id)
        else:
            # Set the block to the next level and schedule it for broadcasting
            redis.delete_sync(storage_error_key(block_id))
            set_current_block_level_sync(block_id, level + 1)
            schedule_block_for_broadcast_sync(block_id)


def get_all_verifications_for_block_sync(block_id: str) -> List[Set[str]]:
    """Get an array of the sets of chain_ids for properly recieved receipts from a higher level for a certain block (sync)
    Args:
        block_id: block_id to check for received receipts
    Returns:
        List of sets of strings (of chain ids). List[0] is for L2 receipts, List[1] is for L3 receipts, etc
    """
    transaction = redis.pipeline_sync()
    transaction.smembers(verifications_key(block_id, 2))
    transaction.smembers(verifications_key(block_id, 3))
    transaction.smembers(verifications_key(block_id, 4))
    transaction.smembers(verifications_key(block_id, 5))
    result = transaction.execute()
    # Decode the results because this used a raw redis pipeline
    for i in range(len(result)):
        decoded_set = set()
        for chain in result[i]:
            decoded_set.add(chain.decode("ascii"))
        result[i] = decoded_set
    return result


def get_receieved_verifications_for_block_and_level_sync(block_id: str, level: int) -> set:
    """Get a set of chain_ids for properly receieved receipts from a higher level for a certain block (sync)
    Args:
        block_id: block_id to check for received receipts
        level: Which higher level of receipts to fetch for block_id
    Returns:
        Python set of chain ids (str)
    """
    return redis.smembers_sync(verifications_key(block_id, level))


async def get_receieved_verifications_for_block_and_level_async(block_id: str, level: int) -> set:
    """Get a set of chain_ids for properly receieved receipts from a higher level for a certain block (async)
    Args:
        block_id: block_id to check for received receipts
        level: Which higher level of receipts to fetch for block_id
    Returns:
        Python set of chain ids (str)
    """
    return await redis.smembers_async(verifications_key(block_id, level))


def remove_block_from_broadcast_system_sync(block_id: str) -> None:
    """Clean up a block from the verifications/broadcast system (sync)

    This should be called when a block has received all necessary verifications
    and no longer needs to be involved with the broadcast system

    Args:
        block_id: block_id to remove from the system
    """
    # Make a multi exec redis transaction for less overhead
    transaction = redis.pipeline_sync()

    transaction.zrem(IN_FLIGHT_KEY, block_id)
    transaction.delete(state_key(block_id))
    transaction.delete(storage_error_key(block_id))
    for i in range(2, 6):
        transaction.delete(verifications_key(block_id, i))
    # This one is for the claim check from matchmaking that is saved locally
    transaction.hdel(CLAIM_CHECK_KEY, block_id)

    transaction.execute()


async def remove_block_from_broadcast_system_async(block_id: str) -> None:
    """Clean up a block from the verifications/broadcast system (async)

    This should be called when a block has received all necessary verifications
    and no longer needs to be involved with the broadcast system

    Args:
        block_id: block_id to remove from the system
    """
    # Make a multi exec redis transaction for less overhead
    transaction = await redis.multi_exec_async()

    transaction.zrem(IN_FLIGHT_KEY, block_id)
    transaction.delete(state_key(block_id))
    transaction.delete(storage_error_key(block_id))
    for i in range(2, 6):
        transaction.delete(verifications_key(block_id, i))
    # This one is for the claim check from matchmaking that is saved locally
    transaction.hdel(CLAIM_CHECK_KEY, block_id)

    await transaction.execute()

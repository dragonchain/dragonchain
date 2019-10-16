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
import re
import time
import json
import asyncio
from typing import Any, Set, Optional, cast, List, Dict

import aiohttp

from dragonchain.broadcast_processor import broadcast_functions
from dragonchain.lib import authorization
from dragonchain.lib import matchmaking
from dragonchain.lib import error_reporter
from dragonchain.lib.dao import block_dao
from dragonchain.lib import dragonnet_config
from dragonchain.lib import keys
from dragonchain.lib import crypto
from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib.interfaces import storage

BROADCAST = os.environ["BROADCAST"]
LEVEL = os.environ["LEVEL"]
HTTP_REQUEST_TIMEOUT = 30  # seconds
BROADCAST_RECEIPT_WAIT_TIME = 35  # seconds
# TODO Make L5 wait time dynamic
BROADCAST_RECEIPT_WAIT_TIME_L5 = 43200  # seconds

VERIFICATION_NOTIFICATION: Dict[str, List[str]] = {}
if os.environ.get("VERIFICATION_NOTIFICATION") is not None:
    VERIFICATION_NOTIFICATION = cast(Dict[str, List[str]], json.loads(os.environ["VERIFICATION_NOTIFICATION"]))


_log = logger.get_logger()
# For these variables, we are sure to call setup() when initializing this module before using it, so we ignore type error for None
_requirements: dict = {}


def setup() -> None:
    """
    Setup the module-level variables for the broadcast processor
    """
    if LEVEL != "1" or BROADCAST == "false":
        raise RuntimeError("Broadcast processor should not be running on this node.")

    global _requirements
    _requirements = dragonnet_config.DRAGONNET_CONFIG

    _log.info(f"Node requirements: {_requirements}")


def needed_verifications(level: int) -> int:
    """Get the number of needed verifications for a certain level from configuration metadata
    Args:
        level: level to check for required verification count (2-5)
    Returns:
        Int of the number of required receipts
    """
    return _requirements[f"l{level}"]["nodesRequired"]


def chain_id_set_from_matchmaking_claim(claim: dict, level: int) -> Set[str]:
    """Get a set of chain ids from a matchmaking claim of a particular level
    Args:
        claim: dictionary of claim from matchmaking
        level: level to get the set of chains for
    Returns:
        set of chain ids
    """
    return set(claim["validations"][f"l{level}"].keys())


def make_broadcast_futures(session: aiohttp.ClientSession, block_id: str, level: int, chain_ids: set) -> Optional[Set[asyncio.Task]]:
    """Initiate broadcasts for a block id to certain higher level nodes
    Args:
        session: aiohttp session to use for making http requests
        block_id: the block id to broadcast
        level: higher level of the chain_ids to broadcast to
        chain_ids: set of (level) chains to broadcast to
    Returns:
        Set of asyncio futures for the http requests initialized (None if it was not possible to get broadcast dto)
    """
    path = "/v1/enqueue"
    broadcasts = set()
    try:
        broadcast_dto = block_dao.get_broadcast_dto(level, block_id)
    except exceptions.NotEnoughVerifications as e:
        _log.warning(f"[BROADCAST PROCESSOR] {str(e)}")
        _log.info(f"[BROADCAST PROCESSOR] Will attempt to broadcast block {block_id} next run")
        broadcast_functions.increment_storage_error_sync(block_id, level)
        return None
    _log.debug(f"[BROADCAST PROCESSOR] Sending broadcast(s) for {block_id} level {level}:\n{broadcast_dto}")
    for chain in chain_ids:
        try:
            headers, data = authorization.generate_authenticated_request("POST", chain, path, broadcast_dto)
            if level != 5:
                headers["deadline"] = str(BROADCAST_RECEIPT_WAIT_TIME)
            url = f"{matchmaking.get_dragonchain_address(chain)}{path}"
            _log.info(f"[BROADCAST PROCESSOR] Firing transaction for {chain} (level {level}) at {url}")
            broadcasts.add(asyncio.create_task(session.post(url=url, data=data, headers=headers, timeout=HTTP_REQUEST_TIMEOUT)))
        except Exception:
            _log.exception(f"[BROADCAST PROCESSOR] Exception trying to broadcast to {chain}")
    return broadcasts


def get_level_from_storage_location(storage_location: str) -> Optional[str]:
    result = re.search("BLOCK/.*?-l([2-5])-", storage_location)
    if result is None:
        return None
    return result.group(1)


def get_notification_urls(key: str) -> set:
    try:
        urls = set(VERIFICATION_NOTIFICATION[key])
    except KeyError:
        urls = set()
    return urls


def sign(message: bytes) -> str:
    return keys.get_my_keys().make_signature(message, crypto.SupportedHashes.sha256)


def get_all_notification_endpoints(level: str) -> set:
    return get_notification_urls("all").union(get_notification_urls(f"l{level}"))


async def process_verification_notifications(session: aiohttp.ClientSession) -> None:
    """Main function for the verification notification broadcast system

    Retrieves verifications that need to be processed and sends http requests

    Args:
        session: aiohttp session for http requests
    """
    if VERIFICATION_NOTIFICATION:
        futures = set()
        for storage_location in await broadcast_functions.get_notification_verifications_for_broadcast_async():
            verification_bytes = storage.get(storage_location)
            level = get_level_from_storage_location(storage_location)
            if level is None:
                _log.error(f"Unable to parse level value from string {storage_location}. Removing verification notification from set.")
                broadcast_functions.remove_notification_verification_for_broadcast_async(storage_location)
                continue
            signature = sign(verification_bytes)
            for url in get_all_notification_endpoints(level):
                future = send_notification_verification(session, url, verification_bytes, signature, storage_location)
                futures.add(asyncio.ensure_future(future))
        try:
            await asyncio.gather(*futures, return_exceptions=True)  # "Fire & forget"
        except Exception:
            _log.exception("Error while notifying verification")


async def send_notification_verification(
    session: aiohttp.ClientSession, url: str, verification_bytes: bytes, signature: str, redis_list_value: str
) -> None:
    """ Send a notification verification to a preconfigured address

    This is the actual async broadcast of a single notification at its most atomic

    Args:
        session: aiohttp session for http requests
        url: The url to which bytes should be POSTed
        verification_bytes: the verification object read from disk as bytes
        signature: The signature of the bytes, signed by this dragonchain
        redis_list_value: the key within a redis set which should be removed after successful http request

    Returns:
        None
    """
    _log.debug(f"Notification -> {url}")
    resp = await session.post(
        url=url, data=verification_bytes, headers={"dragonchainId": keys.get_public_id(), "signature": signature}, timeout=HTTP_REQUEST_TIMEOUT
    )
    _log.debug(f"Notification <- {resp.status} {url}")
    await broadcast_functions.remove_notification_verification_for_broadcast_async(redis_list_value)


async def process_blocks_for_broadcast(session: aiohttp.ClientSession) -> None:
    """Main function of the broadcast processor

    Retrieves blocks that need to be processed, gets matchmaking claims for blocks,
    updates claims to get new chains if existing ones aren't responding,
    then sends broadcasts to chains, and loops

    Args:
        session: aiohttp session for http requests
    """
    # Unfortunately, this is a really long method because it uses a large loop which must be broken
    # or continued at various points in the process, and so can't be necessarily easily broken up
    request_futures: set = set()
    # Get all the relevant blocks for this run (anything scheduled until 'now')
    for block_id, score in await broadcast_functions.get_blocks_to_process_for_broadcast_async():
        _log.info(f"[BROADCAST PROCESSOR] Checking block {block_id}")
        current_level = await broadcast_functions.get_current_block_level_async(block_id)
        try:
            claim: Any = matchmaking.get_or_create_claim_check(block_id, _requirements)
        except exceptions.InsufficientFunds:
            _log.warning("[BROADCAST PROCESSOR] Out of funds! Will not broadcast anything for 30 minutes")
            await asyncio.sleep(1800)  # Sleep for 30 minutes if insufficient funds
            break
        except exceptions.NotFound:
            _log.warning("Matchmaking does not have enough matches to create a claim check")
            # Schedule this block for 5 minutes later, so we don't spam matchmaking every second if there aren't matches available
            await broadcast_functions.schedule_block_for_broadcast_async(block_id, int(time.time()) + 300)
            continue
        claim_chains = chain_id_set_from_matchmaking_claim(claim, current_level)
        if score == 0:
            # If this block hasn't been broadcast at this level before (score is 0)
            _log.info(f"[BROADCAST PROCESSOR] Block {block_id} Level {current_level} not broadcasted yet. Broadcasting to all chains in claim")
            # Make requests for all chains in the claim
            futures = make_broadcast_futures(session, block_id, current_level, claim_chains)
            if futures is None:
                # This occurs when make_broadcast_futures failed to create the broadcast dto (need to process this block later)
                continue
            request_futures.update(futures)
            # Schedule this block to be re-checked after BROADCAST_RECEIPT_WAIT_TIME more seconds have passed
            await broadcast_functions.schedule_block_for_broadcast_async(
                block_id, int(time.time()) + (BROADCAST_RECEIPT_WAIT_TIME if current_level != 5 else BROADCAST_RECEIPT_WAIT_TIME_L5)
            )
        else:
            # Block has been broadcast at this level before. Figure out which chains didn't respond in time
            current_verifications = await broadcast_functions.get_receieved_verifications_for_block_and_level_async(block_id, current_level)
            if len(current_verifications) < needed_verifications(current_level):
                # For each chain that didn't respond
                for chain in claim_chains.difference(current_verifications):
                    _log.info(f"[BROADCAST PROCESSOR] Chain {chain} didn't respond to broadcast in time. Fetching new chain")
                    try:
                        claim = matchmaking.overwrite_no_response_node(block_id, current_level, chain)
                    except exceptions.NotFound:
                        _log.warning(f"Matchmaking does not have enough matches to update this claim check with new chains for level {current_level}")
                        claim = None
                        break
                # Can't continue processing this block if the claim wasn't updated
                if claim is None:
                    # Schedule for 5 minutes later, so we don't spam matchmaking every second if there aren't matches
                    await broadcast_functions.schedule_block_for_broadcast_async(block_id, int(time.time()) + 300)
                    continue
                new_claim_chains = chain_id_set_from_matchmaking_claim(claim, current_level)
                # Make requests for all the new chains
                futures = make_broadcast_futures(session, block_id, current_level, new_claim_chains.difference(current_verifications))
                if (
                    futures is None
                ):  # This occurs when make_broadcast_futures failed to create the broadcast dto (we need to process this block later)
                    continue
                request_futures.update(futures)
                # Schedule this block to be re-checked after BROADCAST_RECEIPT_WAIT_TIME more seconds have passed
                await broadcast_functions.schedule_block_for_broadcast_async(
                    block_id, int(time.time()) + (BROADCAST_RECEIPT_WAIT_TIME if current_level != 5 else BROADCAST_RECEIPT_WAIT_TIME_L5)
                )
            else:
                if current_level >= 5:
                    # If level 5, block needs no more verifications; remove it from the broadcast system
                    _log.warning(
                        f"[BROADCAST PROCESSOR] Block {block_id} has enough verifications at level {current_level}. Removing from broadcast system"
                    )
                    await broadcast_functions.remove_block_from_broadcast_system_async(block_id)
                else:
                    # Promote the block with enough verifications at this level
                    _log.warning(f"[BROADCAST PROCESSOR] Block {block_id} has enough verifications at level {current_level}. Promoting to next level")
                    await broadcast_functions.set_current_block_level_async(block_id, current_level + 1)
                    await broadcast_functions.schedule_block_for_broadcast_async(block_id)
    # Wait for all the broadcasts in this run to finish before returning/looping
    await asyncio.gather(*request_futures, return_exceptions=True)


async def loop() -> None:
    """
    Main loop for the broadcast processor
    """
    session = aiohttp.ClientSession()
    try:
        while True:
            await asyncio.sleep(1)
            await process_blocks_for_broadcast(session)
            await process_verification_notifications(session)
    except Exception:
        await session.close()
        raise


def error_handler(loop: "asyncio.AbstractEventLoop", context: dict) -> None:
    exception = context.get("exception")
    if exception:
        message = error_reporter.get_exception_message(exception)
        error_reporter.report_exception(exception, message)
        loop.stop()
        loop.close()


if __name__ == "__main__":
    try:
        setup()
        event_loop = asyncio.get_event_loop()
        event_loop.set_exception_handler(error_handler)
        event_loop.run_until_complete(loop())
    except Exception as e:
        error_reporter.report_exception(e, "Broadcast processor error")
        raise

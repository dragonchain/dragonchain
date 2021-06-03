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
import json

import requests

from dragonchain.lib import authorization
from dragonchain.lib.dao import block_dao
from dragonchain.lib.dao import interchain_dao
from dragonchain.lib.interfaces import storage
from dragonchain.lib.database import redis
from dragonchain.lib import keys
from dragonchain import exceptions
from dragonchain import logger

LEVEL = os.environ["LEVEL"]
STAGE = os.environ["STAGE"]
REREGISTER_TIMING_KEY = "matchmaking:registration-still-current"
REREGISTER_TIME_AMOUNT = 1500  # 25 Min (Matchmaking forgets every 30)
REQUEST_TIMEOUT = 30
if STAGE == "prod":
    MATCHMAKING_ADDRESS = "https://matchmaking.api.dragonchain.com"
else:
    MATCHMAKING_ADDRESS = "https://matchmaking-dev.api.dragonchain.com"


_log = logger.get_logger()


def get_dragonchain_address(dragonchain_id: str) -> str:
    """Return the endpoint for a particular dragonchain
    Args:
        dragonchain_id: dragonchain id to fetch the endpoint
    Returns:
        String of dragonchain endpoint
    """
    return get_registration(dragonchain_id)["url"]


def get_matchmaking_config() -> dict:
    """Return the endpoint for a particular dragonchain
    Args:
        dragonchain_id: dragonchain id to fetch the endpoint
    Returns:
        String of dragonchain endpoint
    """
    config = {
        "level": int(os.environ["LEVEL"]),
        "url": os.environ["DRAGONCHAIN_ENDPOINT"],
        "scheme": os.environ.get("PROOF_SCHEME") or "trust",
        "hashAlgo": os.environ["HASH"],
        "version": os.environ["DRAGONCHAIN_VERSION"],
        "encryptionAlgo": os.environ["ENCRYPTION"],
    }

    if os.environ["LEVEL"] == "5":
        try:
            client = interchain_dao.get_default_interchain_client()
            config["network"] = client.get_network_string()
            config["interchainWallet"] = client.address
        except exceptions.NotFound:
            _log.warning("L5 chain does not have a default interchain network set")
        config["funded"] = bool(redis.get_sync("dc:isFunded", decode=False))
        config["broadcastInterval"] = float(os.environ.get("BROADCAST_INTERVAL") or "2")
    return config


def get_claim_request_dto(requirements: dict, block_id: str, transaction_count: int) -> dict:
    """Get the claim request DTO for matchmaking
    Args:
        requirements: matchmaking requirements for this block
        block_id: relevant block_id
        transactionCount: number of transactions in this block
    Returns:
        DTO as a dict
    """
    # Noqa for typing until we use TypedDict
    return {
        "numL2s": requirements["l2"].get("nodesRequired"),  # noqa: T484
        "numL3s": requirements["l3"].get("nodesRequired"),  # noqa: T484
        "numL4s": requirements["l4"].get("nodesRequired"),  # noqa: T484
        "numL5s": requirements["l5"].get("nodesRequired"),  # noqa: T484
        "blockId": str(block_id),
        "transactionCount": transaction_count,
    }


def update_funded_flag(flag_value: bool) -> None:
    key = "dc:isFunded"
    if flag_value:
        redis.set_sync(key, "a")  # Value does not matter
    else:
        redis.delete_sync(key)
    register()


def get_overwrite_no_response_dto(claim: dict, higher_level_node: str, higher_level: int) -> dict:
    """Get the DTO for updating a claim request which has an expired node
    Args:
        claim: Actual stored claim object to update
        higher_level_node: id of the node to replace
        higher_level: dragonchain level of the node to replace
    Returns:
        DTO to send to matchmaking in order to update the claim
    """
    return {"claim": claim, "dc_id": higher_level_node, "level": higher_level}


def register(retry: bool = True) -> None:
    """Register self with matchmaking
    Args:
        retry: Whether or not to retry this request if it fails
    """
    path = "/registration"
    body = get_matchmaking_config()
    body["token"] = os.environ.get("REGISTRATION_TOKEN")
    make_matchmaking_request("POST", path, body, retry)
    redis.set_sync(REREGISTER_TIMING_KEY, "a", ex=REREGISTER_TIME_AMOUNT)  # Value doesn't matter


def renew_registration_if_necessary() -> None:
    """Check and renew matchmaking registration if it's time"""
    if not redis.get_sync(REREGISTER_TIMING_KEY):
        register()


def get_registration(dc_id: str) -> dict:
    """Retrieve matchmaking config for any registered chain
    Args:
        dc_id: chain id to get registration data for
    Returns:
        Dictionary of the identity json returned by matchmaking
    Raises:
        exceptions.NotFound if matchmaking sends back an empty response
    """
    path = f"/registration/{dc_id}"
    response = make_matchmaking_request("GET", path, authenticated=False)
    registration = response.json()
    if not registration:
        raise exceptions.NotFound(f"Registration not found for {dc_id}")
    return registration


def update_registration(new_data: dict) -> None:
    try:
        _log.info(f"[MATCHMAKING] Putting matchmaking config in storage: {new_data}")
        matchmaking_config = storage.get_json_from_object("MATCHMAKING_CONFIG.json")
        matchmaking_config.update(new_data)
        storage.put_object_as_json("MATCHMAKING_CONFIG.json", matchmaking_config)
        register()
    except Exception:
        raise exceptions.MatchmakingError("Failure updating matchmaking data")


def create_claim_check(block_id: str, requirements: dict) -> dict:
    """Call matchmaking to create a claimcheck for a block
    Args:
        block_id: block id to create a claim check for
        requirements: requirements dict for this chain
    Returns:
        Parsed claim check (as dict) from matchmaking
    """
    broadcast_dto = block_dao.get_broadcast_dto(2, block_id)
    transaction_count = len(broadcast_dto["payload"]["transactions"])
    claim_request_dto = get_claim_request_dto(requirements, block_id, transaction_count)
    path = "/claim-check"
    response = make_matchmaking_request("POST", path, claim_request_dto)
    claim_check = response.json()
    cache_claim_check(block_id, claim_check)
    return claim_check


def get_claim_check(block_id: str) -> dict:
    """Get a claim check that already exists (memoized)
    Args:
        block_id: the block id of the claim check to fetch
    Returns:
        Parsed claim check (as dict)
    """
    claim_check = redis.hget_sync("broadcast:claimcheck", block_id, decode=False)
    if claim_check is not None:
        return json.loads(claim_check)
    path = f"/claim-check?blockId={block_id}&dcId={keys.get_public_id()}"
    response = make_matchmaking_request("GET", path)
    new_claim_check = response.json()
    cache_claim_check(block_id, new_claim_check)
    return new_claim_check


def get_or_create_claim_check(block_id: str, requirements: dict) -> dict:
    """Get a claim check for a block if it already exists, else create a new one
    Args:
        block_id: block_id for the claim check
        requirements: requirements for the claim check (if it needs to create one)
    Returns:
        Dict of claim check
    """
    try:
        return get_claim_check(block_id)
    except Exception:  # nosec (We don't care why getting a claim check failed, we will simply request a new one from matchmaking)
        pass
    return create_claim_check(block_id, requirements)


def get_claimed_txn_count(l1_dc_id: str, block_id: str) -> int:
    """Get the amount of transactions that were declared for a certain claim check
    Args:
        l1_dc_id: the id of the chain with the claim check
        block_id: the block id of the claim check
    Returns:
        Number of transactions matchmaking reported for this claim check
    """
    path = f"/claim-check?dcId={l1_dc_id}&blockId={block_id}&transactionCount=1"
    response = make_matchmaking_request("GET", path)
    claim_check = response.json()
    return claim_check["transactionCount"]


def overwrite_no_response_node(block_id: str, higher_level: int, higher_level_node: str) -> dict:
    """Update a claim check which has had a node that didn't respond in time
    Args:
        block_id: The block id for the claim that needs to be updated
        higher_level: the level of the node to replace
        higher_level_node: the id of the node to replace
    Returns:
        Updated claim check
    """
    claim = get_claim_check(block_id)
    body = get_overwrite_no_response_dto(claim, higher_level_node, higher_level)
    return update_claim_check(block_id, body)


def update_claim_check(block_id: str, data: dict) -> dict:
    """Update a claim check that already exists
    Args:
        block_id: block id of the claim check to update
        data: to update the claim check with
    Returns:
        Updated claim check from matchmaking
    """
    unique_id = f"{keys.get_public_id()}-{block_id}"
    path = f"/claim-check/{unique_id}"
    response = make_matchmaking_request("PUT", path, data)
    claim_check = response.json()
    cache_claim_check(block_id, claim_check)
    return claim_check


def add_receipt(l1_block_id: str, level: int, dc_id: str, block_id: str, proof: str) -> None:
    """Add a receipt to a claim check and cache the new claim check
    Args:
        l1_block_id: the level 1 block id of the claim check
        level: the level of the verification
        dc_id: the chain id of the verification
        block_id: the block id of the verification
        proof: the proof from the block of the verification
    """
    claim_check = get_claim_check(l1_block_id)
    try:
        data = {}
        data["blockId"] = block_id
        data["signature"] = proof
        _log.info(f"Adding to local matchmaking claim: {data}")
        claim_check["validations"][f"l{level}"][dc_id] = data
        _log.info(f"ADDING NEW RECEIPT FOR BLOCK {block_id} TO CLAIM CHECK FROM LEVEL {level}: {claim_check}")
        cache_claim_check(l1_block_id, claim_check)
    except Exception:
        _log.exception("Failure to add receipt to claimcheck")


def resolve_claim_check(claim_check_id: str) -> None:
    """Call matchmaking to delete a claim check for some reason
    Args:
        claim_check_id: the id of the claim check to delete
    """
    make_matchmaking_request("DELETE", f"/claim-check/{claim_check_id}")


def make_matchmaking_request(
    http_verb: str, path: str, json_content: dict = None, retry: bool = True, authenticated: bool = True
) -> requests.Response:
    """Make an authenticated request to matchmaking and return the response
    Args:
        http_verb: GET, POST, etc
        path: path of the request
        json_content: OPTIONAL if the request needs a post body, include it as a dictionary
        retry: boolean whether or not to recursively retry on recoverable errors (i.e. no auth, missing registration)
            Note: This should not be provided manually, and is only for recursive calls within the function it
        authenticated: boolean whether or not this matchmaking endpoint is authenticated
    Returns:
        Requests response object
    Raises:
        exceptions.MatchmakingError when unexpected matchmaking error occurs
        exceptions.InsufficientFunds when matchmaking responds with payment required
        exceptions.NotFound when matchmaking responds with a 404
    """
    if json_content is None:
        json_content = {}
    http_verb = http_verb.upper()
    _log.info(f"[MATCHMAKING] Performing {http_verb} request to {path} with data: {json_content}")
    headers, data = None, None
    if authenticated:
        headers, data = authorization.generate_authenticated_request(http_verb, "matchmaking", path, json_content)
    else:
        data = json.dumps(json_content, separators=(",", ":")).encode("utf-8") if json_content else b""
        headers = {"Content-Type": "application/json"} if json_content else {}

    response = requests.request(method=http_verb, url=f"{MATCHMAKING_ADDRESS}{path}", headers=headers, data=data, timeout=REQUEST_TIMEOUT)

    if response.status_code < 200 or response.status_code >= 300:
        if retry and response.status_code == 401 and authenticated:
            _log.warning("[MATCHMAKING] received 401 from matchmaking. Registering new key with matchmaking and trying again")
            authorization.register_new_key_with_matchmaking()
            return make_matchmaking_request(http_verb=http_verb, path=path, json_content=json_content, retry=False, authenticated=authenticated)
        elif retry and response.status_code == 403 and authenticated:
            _log.warning(
                "[MATCHMAKING] received 403 from matchmaking. Registration is expired or Dragon Net config is invalid. Re-registering and trying again"
            )
            register(retry=False)
            return make_matchmaking_request(http_verb=http_verb, path=path, json_content=json_content, retry=False, authenticated=authenticated)
        elif response.status_code == 402:
            raise exceptions.InsufficientFunds("received insufficient funds (402) from matchmaking")
        elif response.status_code == 404:
            raise exceptions.NotFound("Not found (404) from matchmaking")
        elif response.status_code == 409:
            raise exceptions.UnableToUpdate("Matchmaking could not find enough nodes to verify this block")
        elif response.status_code >= 500:
            raise exceptions.MatchmakingRetryableError(f"[MATCHMAKING] Server error {response.status_code} from matchmaking")
        raise exceptions.MatchmakingError(
            f"Received unexpected response code {response.status_code} from matchmaking with response:\n{response.text}"
        )

    return response


def cache_claim_check(block_id: str, claim_check: dict) -> None:
    """Cache a claim check in redis
    Args:
        block_id: the block id of the claim check that's being cached
        claim_check: the actual claim check to cache
    """
    try:
        redis.hset_sync("broadcast:claimcheck", str(block_id), json.dumps(claim_check, separators=(",", ":")))
    except Exception:
        _log.exception("Failure uploading claim to storage")

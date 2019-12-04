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
import datetime
import random
import base64
from typing import Optional, Tuple

import requests

from dragonchain.lib.dto import api_key_model
from dragonchain.lib.dao import api_key_dao
from dragonchain.lib import matchmaking
from dragonchain.lib import crypto
from dragonchain.lib import keys
from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib.database import redis

RATE_LIMIT = int(os.environ["RATE_LIMIT"])
TIMEOUT_SEC = 600
MATCHMAKING_KEY_LOCATION = "authorization:matchmaking"
REQUEST_PREFIX_KEY = "request:"

_log = logger.get_logger()


def get_now_datetime() -> datetime.datetime:
    """Return a datetime method for utcnow (used for easy stubbing in tests)
    Returns:
        datetime object of now in UTC
    """
    return datetime.datetime.utcnow()


def get_supported_hmac_hash(hash_type_str: str) -> crypto.SupportedHashes:
    """Return a crypto SupportedHashes enum type from a string hash type
    Args:
        hash_type_str: String hashtype, i.e. SHA256
    Returns:
        appropriate crypto.SupportedHashes enum value
    Raises:
        ValueError when bad hash_type_str
    """
    if hash_type_str == "SHA256":
        return crypto.SupportedHashes.sha256
    elif hash_type_str == "BLAKE2b512":
        return crypto.SupportedHashes.blake2b
    elif hash_type_str == "SHA3-256":
        return crypto.SupportedHashes.sha3_256
    else:
        raise ValueError(f"{hash_type_str} is an unsupported HMAC hash type")


def get_hmac_message_string(
    http_verb: str, full_path: str, dcid: str, timestamp: str, content_type: str, content: bytes, hash_type: crypto.SupportedHashes
) -> str:
    """Generate the hmac message string for a dragonchain authorization request
    Args:
        http_verb: HTTP verb of the request
        full_path: full path of the request after the FQDN (including any query parameters) (i.e. /chains/transaction)
        dcid: dragonchain id of the request (must match dragonchain header)
        timestamp: timestamp of the request (must match timestamp header)
        content-type: content-type header of the request (if it exists)
        content: bytes object of the body of the request (if it exists)
        hash_type: crypto SupportedHashes enum type to use with hashing the content
    Returns:
        Message string to use when generating the hmac
    """
    hash_method = crypto.get_hash_method(hash_type)
    hashed_content = base64.b64encode(hash_method(content).digest()).decode("ascii")
    return f"{http_verb.upper()}\n{full_path}\n{dcid}\n{timestamp}\n{content_type}\n{hashed_content}"


def get_authorization(
    auth_key_id: str, auth_key: str, http_verb: str, full_path: str, dcid: str, timestamp: str, content_type: str, content: bytes, hmac_hash_type: str
) -> str:
    """Create an authorization header for making requests to dragonchains
    Args:
        auth_key_id: ID string of the auth key to use
        auth_key: String of the auth key to use
        http_verb: HTTP verb of the request
        full_path: full path of the request after the FQDN (including any query parameters) (i.e. /chains/transaction)
        dcid: dragonchain id of the request (must match dragonchain header)
        timestamp: timestamp of the request (must match timestamp header)
        content-type: content-type header of the request (if it exists)
        content: bytes object of the body of the request (if it exists)
        hmac_hash_type: HMAC hash type string that's supported by get_supported_hmac_hash (i.e. SHA256)
    Returns:
        String of generated authorization header
    """
    version = "1"
    supported_hash = get_supported_hmac_hash(hmac_hash_type)
    message_string = get_hmac_message_string(http_verb, full_path, dcid, timestamp, content_type, content, supported_hash)
    hmac = base64.b64encode(crypto.create_hmac(supported_hash, auth_key, message_string)).decode("ascii")
    return f"DC{version}-HMAC-{hmac_hash_type} {auth_key_id}:{hmac}"


def save_matchmaking_auth_key(auth_key: str) -> bool:
    """Register a new matchmaking auth key. !This will overwrite the existing matchmaking key for this chain!
    Args:
        auth_key: auth_key to add for matchmaking
    Returns:
        Boolean if successful
    """
    try:
        redis.set_sync(MATCHMAKING_KEY_LOCATION, auth_key)
        return True
    except Exception:
        return False


def get_matchmaking_key() -> Optional[str]:
    """Retrieve the auth key to use for hmac with matchmaking
    Returns:
        The base64 encoded auth key string (None if not found)
    """
    return redis.get_sync(MATCHMAKING_KEY_LOCATION)


def register_new_interchain_key_with_remote(interchain_dcid: str) -> api_key_model.APIKeyModel:
    """Make a new auth key and register it with a remote dragonchain for inter-level communication
    Args:
        interchain_dcid: chain id of the interchain sharing this key
    Returns:
        API key model for the newly shared key
    Raises:
        RuntimeError when bad response from chain or couldn't save to storage
    """
    # We need to estabilish a shared HMAC key for this chain before we can post
    new_interchain_key = api_key_model.new_from_scratch(interchain_dcid=interchain_dcid)
    signature = keys.get_my_keys().make_signature(f"{interchain_dcid}_{new_interchain_key.key}".encode("utf-8"), crypto.SupportedHashes.sha256)
    new_key = {"dcid": keys.get_public_id(), "key": new_interchain_key.key, "signature": signature}
    try:
        r = requests.post(f"{matchmaking.get_dragonchain_address(interchain_dcid)}/v1/interchain-auth-register", json=new_key, timeout=30)
    except Exception as e:
        raise RuntimeError(f"Unable to register shared auth key with dragonchain {interchain_dcid}\nError: {e}")
    if r.status_code < 200 or r.status_code >= 300:
        raise RuntimeError(f"Unable to register shared auth key with dragonchain {interchain_dcid}\nStatus code: {r.status_code}")
    api_key_dao.save_api_key(new_interchain_key)
    return new_interchain_key


def register_new_key_with_matchmaking() -> str:
    """Make a new auth key and register it with matchmaking
    Returns:
        auth key string of the newly shared key
    Raises:
        RuntimeError when bad response from chain or couldn't save to storage
    """
    auth_key = api_key_model.gen_auth_key()
    signature = keys.get_my_keys().make_signature(f"matchmaking_{auth_key}".encode("utf-8"), crypto.SupportedHashes.sha256)
    new_key = {"dcid": keys.get_public_id(), "key": auth_key, "signature": signature}
    try:
        r = requests.post(f"{matchmaking.MATCHMAKING_ADDRESS}/auth-register", json=new_key, timeout=30)
    except Exception as e:
        raise RuntimeError(f"Unable to register shared auth key with matchmaking\nError: {e}")
    if r.status_code < 200 or r.status_code >= 300:
        raise RuntimeError(f"Unable to register shared auth key with matchmaking\nStatus code: {r.status_code}")
    if not save_matchmaking_auth_key(auth_key):
        raise RuntimeError("Unable to add new interchain auth key to storage")
    return auth_key


def generate_authenticated_request(
    http_verb: str, dcid: str, full_path: str, json_content: dict = None, hmac_hash_type: str = "SHA256"
) -> Tuple[dict, bytes]:
    """Generate request data (headers and body) for making authenticated http requests to other dragonchains or matchmaking
    Args:
        http_verb: string of the http verb that will be used for this request (i.e. GET, POST, etc)
        dcid: the dragonchain id to make this request for. If this is for matchmaking, specify the string 'matchmaking' instead
        full_path: full path of the request after the FQDN (including any query parameters) (i.e. /matchmaking/2?qty=3)
        json_content: dictionary object to use as the json body of the request (only include if request has a body)
        hmac_hash_type: the hmac hash type to use for this request
    Returns:
        Tuple where index 0 is the headers dictionary to use, and index 1 is the byte data (body) to use for an http request
    """
    if json_content is None:
        json_content = {}
    auth_key = None
    matchmaking = dcid == "matchmaking"
    http_verb = http_verb.upper()
    # First check if we already have a shared HMAC key for sending to this endpoint
    if matchmaking:
        auth_key = get_matchmaking_key()
        if auth_key is None:
            # We need to estabilish a shared HMAC key with matchmaking before we can make a request
            auth_key = register_new_key_with_matchmaking()
    else:
        try:
            auth_key = api_key_dao.get_api_key(dcid, interchain=True).key
        except exceptions.NotFound:
            # We need to estabilish a shared HMAC key for this chain before we can make a request
            auth_key = register_new_interchain_key_with_remote(dcid).key
    timestamp = get_now_datetime().isoformat() + "Z"
    content_type = ""
    content = b""
    if json_content:
        content_type = "application/json"
        content = json.dumps(json_content, separators=(",", ":")).encode("utf-8")
    headers = {
        "timestamp": timestamp,
        "Authorization": get_authorization(
            keys.get_public_id(), auth_key, http_verb, full_path, dcid, timestamp, content_type, content, hmac_hash_type
        ),
    }
    # Only add dragonchain header for inter-dragonchain communication
    if not matchmaking:
        headers["dragonchain"] = dcid
    # Only add content type header if it exists
    if content_type:
        headers["Content-Type"] = content_type
    return headers, content


def signature_is_replay(request_signature: str) -> bool:
    """Check if a request signature is new, and add also mark it as used (if it is new)
    Args:
        request_signature: string of the request id to check
    Returns:
        boolean true if this signature is a replay, false if not
    """
    redis_key = f"{REQUEST_PREFIX_KEY}{request_signature}"
    if redis.get_sync(redis_key, decode=False):
        # If key exists in redis, we return True
        return True
    # Set this new request_signature in redis (value doesn't matter) and return False
    # Set additional 60 seconds from timeout just as a safety in case the chain's clock re-adjusts slightly (NTP)
    redis.set_sync(redis_key, "a", ex=60)
    return False


def should_rate_limit(key_id: str) -> bool:
    """Check if a particular key_id should be rate limited
    Args:
        key_id: The key id to check if it needs to be rate limited
    Returns:
        boolean true if key should be rate limited, false if not
    """
    # Don't rate limit for 0 (not enabled)
    if not RATE_LIMIT:
        return False

    redis_key = f"{REQUEST_PREFIX_KEY}{key_id}"
    current_time = time.time()
    # Get the oldest relevant call
    oldest = redis.lindex_sync(redis_key, RATE_LIMIT - 1, decode=False)
    # If this oldest request has happened less than 1 minute ago, then rate limit
    if oldest and float(oldest) > current_time - 60:
        return True
    # Add this as a request for this key
    redis.lpush_sync(redis_key, str(current_time))
    # Trim the list down to the last <rate_limit> calls (no other calls are relevant)
    # This frees memory from redis, but slows down authorization, so we only do it occasionally
    if random.randint(0, 9) == 0:  # nosec (this isn't needed for cryptographic purposes)
        redis.ltrim_sync(redis_key, 0, RATE_LIMIT - 1)
    return False


def verify_request_authorization(  # noqa: C901
    authorization: str,
    http_verb: str,
    full_path: str,
    dcid: str,
    timestamp: str,
    content_type: str,
    content: bytes,
    interchain: bool,
    api_group: str,
    api_action: str,
    api_name: str,
) -> api_key_model.APIKeyModel:
    """Verify an http request to the webserver
    Args:
        authorization: Authorization header of the request
        http_verb: HTTP Verb of the request (i.e. GET, POST, etc)
        full_path: full path of the request after the FQDN (including any query parameters) (i.e. /chains/transaction)
        dcid: dragonchain header of the request
        timestamp: timestamp header of the request
        content-type: content-type header of the request (if it exists)
        content: byte object of the body of the request (if it exists)
        interchain: boolean whether to use interchain keys to check or not
        api_group: the api group name of this endpoint
        api_action: the CRUD api action of this endpoint ("create", "read", "update", "delete")
        api_name: the api name of this particular endpoint
    Raises:
        exceptions.UnauthorizedException (with message) when the authorization is not valid
        exceptions.ActionForbidden (with message) when the authorization is valid, but the action is not allowed
        exceptions.APIRateLimitException (with message) when rate limit is currently exceeded for the provided api key id
    Returns:
        The api key model used for this request (if successfully authenticated)
    """
    if dcid != keys.get_public_id():
        raise exceptions.UnauthorizedException("Incorrect Dragonchain ID")
    try:
        # Note, noqa for typing on re.searches are because we explicitly catch the exceptions and handle below
        version = re.search("^DC(.*)-HMAC", authorization).group(1)  # noqa: T484
        if version == "1":
            hash_type = re.search("HMAC-(.*) ", authorization).group(1)  # noqa: T484
            try:
                supported_hash = get_supported_hmac_hash(hash_type)
            except ValueError:
                raise exceptions.UnauthorizedException("Unsupported HMAC Hash Type")
            # Make sure clock drift isn't too far to prevent replays
            now = get_now_datetime()
            request_time = None
            # Tolerate given timestamps both with/without decimals of a second
            if "." in timestamp:
                request_time = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
            else:
                request_time = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
            delta = datetime.timedelta(seconds=TIMEOUT_SEC)
            # Allow all requests within +/- TIMEOUT_SEC seconds of the chain's curent time
            if now + delta < request_time or now - delta > request_time:
                raise exceptions.UnauthorizedException("Timestamp of request too skewed")
            hmac_index = authorization.rfind(":")
            if hmac_index == -1:
                raise exceptions.UnauthorizedException("Malformed Authorization Header")
            hmac = base64.b64decode(authorization[hmac_index + 1 :])
            message_string = get_hmac_message_string(http_verb, full_path, dcid, timestamp, content_type, content, supported_hash)
            try:
                auth_key_id = re.search(" (.*):", authorization).group(1)  # noqa: T484
                try:
                    auth_key = api_key_dao.get_api_key(auth_key_id, interchain)
                except exceptions.NotFound:
                    _log.info(f"Authorization failure from key that does not exist {auth_key_id}")
                    raise exceptions.UnauthorizedException("Invalid HMAC Authentication")
                # Check if this key should be rate limited (does not apply to interchain keys)
                if not interchain and should_rate_limit(auth_key_id):
                    raise exceptions.APIRateLimitException(f"API Rate Limit Exceeded. {RATE_LIMIT} requests allowed per minute.")
                if crypto.compare_hmac(supported_hash, hmac, auth_key.key, message_string):
                    # Check if this signature has already been used for replay protection
                    if signature_is_replay(f"{auth_key_id}:{base64.b64encode(hmac).decode('ascii')}"):
                        raise exceptions.UnauthorizedException("Previous matching request found (no replays allowed)")
                    # Check that this key is allowed to perform this action
                    try:
                        if auth_key.is_key_allowed(api_group, api_action, api_name, interchain):
                            # Signature is valid and key is allowed; Return the api key used on success
                            return auth_key
                    except Exception:
                        _log.exception(f"Uncaught exception checking if api key is allowed")
                    raise exceptions.ActionForbidden(f"This key is not allowed to perform {api_name}")
                else:
                    # HMAC doesn't match
                    raise exceptions.UnauthorizedException("Invalid HMAC Authentication")
            except exceptions.DragonchainException:
                raise
            except Exception:
                raise exceptions.UnauthorizedException("Invalid HMAC Format")
        else:
            raise exceptions.UnauthorizedException("Unsupported DC Authorization Version")
    except exceptions.DragonchainException:
        raise
    except Exception:
        raise exceptions.UnauthorizedException("Malformed Authorization Header")

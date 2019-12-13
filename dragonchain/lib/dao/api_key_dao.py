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

from typing import List

from dragonchain.lib.interfaces import storage
from dragonchain.lib.dto import api_key_model
from dragonchain import exceptions
from dragonchain import logger

FOLDER = "KEYS"
INTERCHAIN_FOLDER = "KEYS/INTERCHAIN"
MIGRATION_V1 = "MIGRATION_V1_COMPLETE"

_log = logger.get_logger()


def save_api_key(api_key: api_key_model.APIKeyModel) -> None:
    """Save an api key model to storage"""
    storage.put_object_as_json(
        f"{INTERCHAIN_FOLDER if api_key.interchain else FOLDER}/{api_key.key_id}", api_key.export_as_at_rest(),
    )


def get_api_key(key_id: str, interchain: bool) -> api_key_model.APIKeyModel:
    """Get an api key from storage
    Args:
        key_id: The key id to fetch (public chain id if interchain)
        interchain: Whether or not this is an interchain key
    """
    # Explicitly don't allow permission keys with slashes (may be malicious)
    if "/" in key_id:
        raise exceptions.NotFound
    model = api_key_model.new_from_at_rest(storage.get_json_from_object(f"{INTERCHAIN_FOLDER if interchain else FOLDER}/{key_id}"))
    if model.interchain != interchain:  # Double check the interchain value of the key is what we expect; otherwise panic
        raise RuntimeError(f"Bad interchain key {key_id} found. Expected interchain: {interchain} but got {model.interchain}")
    return model


def list_api_keys(include_interchain: bool) -> List[api_key_model.APIKeyModel]:
    """Retrieve a list of api keys
    Args:
        include_interchain: whether or not to include interchain api keys
    Returns:
        List of api key models
    """
    # Get keys from storage, excluding migration marker and interchain keys
    return_list = []
    for key in storage.list_objects(prefix=FOLDER):
        if (MIGRATION_V1 in key) or (key.startswith("KEYS/INTERCHAIN") and not include_interchain):
            continue
        return_list.append(api_key_model.new_from_at_rest(storage.get_json_from_object(key)))
    return return_list


def delete_api_key(key_id: str, interchain: bool) -> None:
    """Delete an api key from this chain
    Args:
        key_id: The key id to delete (public chain id if interchain)
        interchain: Whether or not this is an interchain key
    """
    if not interchain and key_id.startswith("INTERCHAIN"):
        raise RuntimeError("Attempt to remove interchain key when not intended")
    storage.delete(f"{INTERCHAIN_FOLDER if interchain else FOLDER}/{key_id}")


def perform_api_key_migration_v1_if_necessary() -> None:
    """Checks if an api key migration needs to be performed, and does so if necessary"""
    try:
        if storage.get(f"{FOLDER}/{MIGRATION_V1}") == b"1":
            # Migration was previously performed. No action necessary
            return
    except exceptions.NotFound:
        pass
    _log.info("Api key migration required. Performing now")
    valid_keys = storage.list_objects(prefix=FOLDER)
    regular_keys = list(filter(lambda x: not x.startswith("KEYS/INTERCHAIN/"), valid_keys))
    interchain_keys = list(filter(lambda x: x.startswith("KEYS/INTERCHAIN/"), valid_keys))
    for key in regular_keys:
        _log.info(f"Migrating {key}")
        api_key = api_key_model.new_from_legacy(storage.get_json_from_object(key), interchain_dcid="")
        save_api_key(api_key)
    for key in interchain_keys:
        _log.info(f"Migrating interchain key {key}")
        interchain_dcid = key[key.find("KEYS/INTERCHAIN/") + 16 :]  # Get the interchain dcid from the key
        api_key = api_key_model.new_from_legacy(storage.get_json_from_object(key), interchain_dcid=interchain_dcid)
        save_api_key(api_key)
    # Save migration marker once complete
    storage.put(f"{FOLDER}/{MIGRATION_V1}", b"1")
    _log.info("Api key migration v1 complete")

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

from typing import Dict, Any, List

from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib import authorization
from dragonchain.lib.interfaces import secrets
from dragonchain.lib.interfaces import storage

FOLDER = "KEYS"

_log = logger.get_logger()


def get_api_key_list_v1() -> Dict[str, List[Dict[str, Any]]]:
    """
    Gets the list of api key IDs
    Returns:
        List of API keys
    """
    keys = storage.list_objects(prefix=FOLDER)
    valid_keys = list(filter(lambda x: not x.startswith("KEYS/WEB_") and not x.startswith("KEYS/SC_") and not x.startswith("KEYS/INTERCHAIN"), keys))
    returned_keys = []
    for key in valid_keys:
        resp = storage.get_json_from_object(key)
        returned_keys.append(
            {"id": str(resp["id"]), "registration_time": int(resp["registration_time"]), "nickname": str(resp.get("nickname") or "")}
        )
    return {"keys": returned_keys}


def create_api_key_v1(nickname: str = "") -> Dict[str, Any]:
    """
    Create a new api key
    Returns:
        newly created API keys
    """
    key = authorization.register_new_auth_key(nickname=nickname)
    return {"key": str(key["key"]), "id": str(key["id"]), "registration_time": int(key["registration_time"]), "nickname": str(key.get("nickname"))}


def delete_api_key_v1(key_id: str) -> None:
    """Delete api key by key ID ONLY if it is not the last key on the chain
    Args:
        key_id: ID of api key to delete
    """
    # Don't allow removal of reserved keys
    if key_id.startswith("SC_") or key_id.startswith("INTERCHAIN") or key_id.startswith("WEB_"):
        raise exceptions.ActionForbidden("cannot delete reserved API keys")
    # Don't allow removal of root keys
    root_key_id = secrets.get_dc_secret("hmac-id")
    if root_key_id == key_id:
        raise exceptions.ActionForbidden("Cannot remove root API key")
    # Delete the actual key after previous checks pass
    if not authorization.remove_auth_key(auth_key_id=key_id, interchain=False):
        raise RuntimeError("Unkown error deleting key from storage")


def get_api_key_v1(key_id: str) -> Dict[str, Any]:
    """Returns the api key information (without the actual key itself) for a key id
    Args:
        key_id: ID of api key to get
        hide_key: remove the api key from the returned key
    Returns:
        API key ID and registration timestamp (if any)
    """
    if key_id.startswith("SC_") or key_id.startswith("WEB_") or key_id.startswith("INTERCHAIN"):
        raise exceptions.NotFound(f"api key with ID {key_id} not found")
    key = storage.get_json_from_object(f"KEYS/{key_id}")
    return {"id": str(key["id"]), "registration_time": int(key["registration_time"]), "nickname": str(key.get("nickname") or "")}


def update_api_key_v1(key_id: str, nickname: str) -> None:
    """Updates the nickname for an existing key
    Args:
        key_id: ID of api key to update
        nickname: new nickname for the given key
    """
    key = storage.get_json_from_object(f"KEYS/{key_id}")
    key["nickname"] = nickname
    storage.put_object_as_json(f"KEYS/{key_id}", key)

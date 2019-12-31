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

from typing import Dict, Any, List, Optional, TYPE_CHECKING

from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib.interfaces import secrets
from dragonchain.lib.dao import api_key_dao
from dragonchain.lib.dto import api_key_model

if TYPE_CHECKING:
    from dragonchain.lib.types import permissions_doc  # noqa: F401 used by typing

_log = logger.get_logger()


def _api_key_model_to_user_dto(api_key: api_key_model.APIKeyModel, with_key: bool = False) -> Dict[str, Any]:
    user_dto = {
        "id": api_key.key_id,
        "registration_time": api_key.registration_time,
        "nickname": api_key.nickname,
        "root": api_key.root,
        "permissions_document": api_key.permissions_document,
    }
    if with_key:
        user_dto["key"] = api_key.key
    return user_dto


def get_api_key_list_v1() -> Dict[str, List[Dict[str, Any]]]:
    """Gets the list of api key IDs
    Returns:
        List of API keys
    """
    keys = api_key_dao.list_api_keys(include_interchain=False)
    returned_keys = []
    for key in keys:
        returned_keys.append(_api_key_model_to_user_dto(key))
    return {"keys": returned_keys}


def create_api_key_v1(nickname: str = "", permissions_document: Optional["permissions_doc"] = None) -> Dict[str, Any]:
    """Create a new api key
    Returns:
        newly created API keys
    """
    key = api_key_model.new_from_scratch(smart_contract=False, nickname=(nickname or ""))
    if permissions_document:
        # This permissions doc that was passed in should have had the schema validated by the webserver route
        key.permissions_document = permissions_document
    api_key_dao.save_api_key(key)
    return _api_key_model_to_user_dto(key, with_key=True)


def delete_api_key_v1(key_id: str) -> None:
    """Delete api key by key ID ONLY if it is not the last key on the chain
    Args:
        key_id: ID of api key to delete
    """
    # Don't allow removal of reserved keys
    if key_id.startswith("SC_") or key_id.startswith("INTERCHAIN"):
        raise exceptions.ActionForbidden("Cannot delete reserved API keys")
    # Don't allow removal of root keys
    if secrets.get_dc_secret("hmac-id") == key_id:
        raise exceptions.ActionForbidden("Cannot remove root API key")
    # Delete the actual key after previous checks pass
    api_key_dao.delete_api_key(key_id=key_id, interchain=False)


def get_api_key_v1(key_id: str) -> Dict[str, Any]:
    """Returns the api key information (without the actual key itself) for a key id
    Args:
        key_id: ID of api key to get
        hide_key: remove the api key from the returned key
    Returns:
        API key ID and registration timestamp (if any)
    """
    if key_id.startswith("INTERCHAIN"):
        raise exceptions.NotFound("Cannot get interchain api keys")
    return _api_key_model_to_user_dto(api_key_dao.get_api_key(key_id, interchain=False))


def update_api_key_v1(key_id: str, nickname: Optional[str] = None, permissions_document: Optional["permissions_doc"] = None) -> Dict[str, Any]:
    """Updates the nickname for an existing key
    Args:
        key_id: ID of api key to update
        nickname: new nickname for the given key
    """
    if key_id.startswith("INTERCHAIN"):
        raise exceptions.ActionForbidden("Cannot modify interchain keys")
    key = api_key_dao.get_api_key(key_id, interchain=False)
    if nickname:
        key.nickname = nickname
    if permissions_document:
        # This permissions doc that was passed in should have had the schema validated by the webserver route
        key.permissions_document = permissions_document
    api_key_dao.save_api_key(key)
    return _api_key_model_to_user_dto(key)

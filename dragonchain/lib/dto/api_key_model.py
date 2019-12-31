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

import time
import string
import secrets
from typing import Dict, Any, Optional, TYPE_CHECKING

from dragonchain.lib.dto import model
from dragonchain import logger

if TYPE_CHECKING:
    from dragonchain.lib.types import permissions_doc  # noqa: F401

_log = logger.get_logger()

# Default permissions document allows all actions except for create/update/delete api keys
DEFAULT_PERMISSIONS_DOCUMENT: "permissions_doc" = {
    "version": "1",
    "default_allow": True,
    "permissions": {"api_keys": {"allow_create": False, "allow_update": False, "allow_delete": False}},
}


def _check_default_endpoint_permission(api_name_permissions: Dict[str, Any], extra_data: Optional[Dict[str, Any]]) -> Optional[bool]:
    """Helper method which parses an endpoint with a default permission policy
    Args:
        api_name_permissions: The specific section of the self.permissions_document for the endpoint being checked
        extra_data: The extra data from is_key_allowed (not used in this function, but required for compatibility)
    Returns:
        Boolean of allowed/disallowed if able to be parsed correctly, else None
    """
    return api_name_permissions.get("allowed")


def _check_create_transaction_permission(api_name_permissions: Dict[str, Any], extra_data: Optional[Dict[str, Any]]) -> Optional[bool]:
    """Method to check if creating a transaction is allowed
    Args:
        api_name_permissions: The specific section of the self.permissions_document for create_transaction
        extra_data: Dictionary with the key "requested_types" which is an iterable of strings of the transaction types to check if allowed
    Returns:
        Boolean if allowed to create the transaction(s)
    """
    if not extra_data:  # Will not have extra data when checking with request authorizer
        return True
    # Will have extra data here when checking in create transaction library functions
    allowed = api_name_permissions.get("allowed")
    transaction_type_permissions = api_name_permissions.get("transaction_types")
    if transaction_type_permissions is not None:
        if allowed is False:
            for txn_type in extra_data["requested_types"]:
                # All transaction types must be explicitly true (since allowed is explicitly false)
                if transaction_type_permissions.get(txn_type) is not True:
                    return False
            return True
        else:
            for txn_type in extra_data["requested_types"]:
                # Only deny if explicitly false (since allowed is not explicitly false)
                if transaction_type_permissions.get(txn_type) is False:
                    return False
    return allowed


ENDPOINT_MAP = {
    "create_api_key": _check_default_endpoint_permission,
    "get_api_key": _check_default_endpoint_permission,
    "list_api_keys": _check_default_endpoint_permission,
    "delete_api_key": _check_default_endpoint_permission,
    "update_api_key": _check_default_endpoint_permission,
    "get_block": _check_default_endpoint_permission,
    "query_blocks": _check_default_endpoint_permission,
    "create_interchain": _check_default_endpoint_permission,
    "update_interchain": _check_default_endpoint_permission,
    "create_interchain_transaction": _check_default_endpoint_permission,
    "list_interchains": _check_default_endpoint_permission,
    "get_interchain": _check_default_endpoint_permission,
    "delete_interchain": _check_default_endpoint_permission,
    "get_default_interchain": _check_default_endpoint_permission,
    "set_default_interchain": _check_default_endpoint_permission,
    "get_interchain_legacy": _check_default_endpoint_permission,
    "create_interchain_transaction_legacy": _check_default_endpoint_permission,
    "get_status": _check_default_endpoint_permission,
    "get_contract": _check_default_endpoint_permission,
    "get_contract_logs": _check_default_endpoint_permission,
    "list_contracts": _check_default_endpoint_permission,
    "create_contract": _check_default_endpoint_permission,
    "update_contract": _check_default_endpoint_permission,
    "delete_contract": _check_default_endpoint_permission,
    "get_contract_object": _check_default_endpoint_permission,
    "list_contract_objects": _check_default_endpoint_permission,
    "create_transaction_type": _check_default_endpoint_permission,
    "delete_transaction_type": _check_default_endpoint_permission,
    "list_transaction_types": _check_default_endpoint_permission,
    "get_transaction_type": _check_default_endpoint_permission,
    "create_transaction": _check_create_transaction_permission,
    "query_transactions": _check_default_endpoint_permission,
    "get_transaction": _check_default_endpoint_permission,
    "get_verifications": _check_default_endpoint_permission,
    "get_pending_verifications": _check_default_endpoint_permission,
}


def gen_auth_key() -> str:
    """Generate an auth key string
    Returns:
        String of the newly generated auth key
    """
    # Note a 43 character key with this keyset gives us ~256 bits of entropy for these auth_keys
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(43))


def new_root_key(key_id: str, key: str) -> "APIKeyModel":
    """Create a new root api key model from only the provided key/key_id
    Args:
        key_id: The key id for this root key
        key: The key for this root key
    Returns:
        Constructed APIKeyModel
    """
    return APIKeyModel(
        key_id=key_id,
        key=key,
        registration_time=int(time.time()),
        root=True,
        nickname="",
        interchain=False,
        permissions_document={"version": "1", "default_allow": True, "permissions": {}},
    )


def new_from_scratch(smart_contract: bool = False, nickname: str = "", interchain_dcid: str = "") -> "APIKeyModel":
    """Create a new api key model from scratch, generating necessary fields
    Args:
        smart_contract: Whether or not this key is for a smart contract
        nickname: The nickname for this api key
        interchain_dcid: The dcid of the interchain (if this is an interchain key; otherwise leave blank)
    Returns:
        Constructed APIKeyModel
    """
    if smart_contract and interchain_dcid:
        raise RuntimeError("Can't create a smart contract api key that is also an interchain key")
    interchain = bool(interchain_dcid)
    if not interchain:
        key_id = "".join(secrets.choice(string.ascii_uppercase) for _ in range(12))
        if smart_contract:
            key_id = f"SC_{key_id}"
        permissions_document = DEFAULT_PERMISSIONS_DOCUMENT
    else:
        key_id = interchain_dcid
        # Default interchain keys aren't allowed any permissions (can still call Dragon Net reserved interchain endpoints)
        permissions_document = {"version": "1", "default_allow": False, "permissions": {}}
    return APIKeyModel(
        key_id=key_id,
        key=gen_auth_key(),
        registration_time=int(time.time()),
        root=False,
        nickname=nickname,
        interchain=interchain,
        permissions_document=permissions_document,
    )


def new_from_at_rest(api_key_data: Dict[str, Any]) -> "APIKeyModel":
    """Construct an api key model from at rest (cached storage)"""
    if api_key_data.get("version") == "1":
        return APIKeyModel(
            key_id=api_key_data["key_id"],
            key=api_key_data["key"],
            registration_time=api_key_data["registration_time"],
            root=api_key_data["root"],
            nickname=api_key_data["nickname"],
            permissions_document=api_key_data["permissions_document"],
            interchain=api_key_data["interchain"],
        )
    else:
        raise NotImplementedError(f"Version {api_key_data.get('version')} is not supported")


def new_from_legacy(api_key_data: Dict[str, Any], interchain_dcid: str) -> "APIKeyModel":
    """Construct an api key model from legacy (pre-4.3.0) api key dto storage"""
    permissions_document = DEFAULT_PERMISSIONS_DOCUMENT
    if interchain_dcid:
        permissions_document = {"version": "1", "default_allow": False, "permissions": {}}
    elif api_key_data.get("root"):
        permissions_document = {"version": "1", "default_allow": True, "permissions": {}}
    return APIKeyModel(
        key_id=api_key_data.get("id") or interchain_dcid,
        key=api_key_data["key"],
        registration_time=api_key_data.get("registration_time") or 0,
        root=api_key_data.get("root") or False,
        nickname=api_key_data.get("nickname") or "",
        interchain=bool(interchain_dcid),
        permissions_document=permissions_document,
    )


class APIKeyModel(model.Model):
    """
    APIKeyModel class is an abstracted representation of an api key
    """

    def __init__(
        self, key_id: str, key: str, registration_time: int, root: bool, nickname: str, interchain: bool, permissions_document: "permissions_doc"
    ):
        self.key_id = key_id
        self.key = key
        self.root = root
        self.registration_time = registration_time
        self.nickname = nickname
        self.interchain = interchain
        self.permissions_document = permissions_document

    def is_key_allowed(
        self, api_resource: str, api_operation: str, api_name: str, interchain: bool, extra_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Checks if this keys is allowed to perform an action for a given api endpoint
        Args:
            api_resource: The resource that the endpoint being checked belongs to. i.e. api_keys, blocks, interchains, etc
            api_operation: The CRUD operation that this endpoint is performing. Should be one of: create, read, update, or delete
            api_name: The exact name of this api action used for permissioning. i.e. create_api_key, list_contracts, get_status, etc
            extra_data: Any extra data required for non-default permission endpoints
        Returns:
            boolean whether or not this key is allowed to perform the action
        """
        # Ensure that if this is a reserved Dragon Net action, only interchain keys can invoke it
        if interchain:
            return self.interchain
        # Interchain keys are not allowed to invoke any other endpoint
        if self.interchain:
            return False

        if self.root:
            return True
        if self.permissions_document.get("version") == "1":
            return self.is_key_allowed_v1(api_resource, api_operation, api_name, extra_data)
        else:
            _log.error(f"Auth from invalid permissioning on key {self.key_id}\nPermissions: {self.permissions_document}")
            raise RuntimeError(f"Invalid permissions document version: {self.permissions_document.get('version')}")

    def is_key_allowed_v1(self, api_resource: str, api_operation: str, api_name: str, extra_data: Optional[Dict[str, Any]] = None) -> bool:
        """Checks if a key is allowed with v1 permissions"""
        allowed = self.permissions_document["default_allow"]

        # Get our per-endpoint validation function now to ensure that api_name is valid before continuing
        try:
            validation_function = ENDPOINT_MAP[api_name]
        except Exception:
            # This should never happen
            _log.exception(f"Error api_name {api_name} is wrong. This should never happen!")
            raise RuntimeError(f"'{api_name}' is not a valid know api_name")

        # Check the 'global' CRUD values
        group_allow = _process_api_resource(self.permissions_document["permissions"], api_operation)
        if group_allow is not None:
            allowed = group_allow

        # Check the specific api resource CRUD values
        api_resource_permissions = self.permissions_document["permissions"].get(api_resource)
        if api_resource_permissions:
            group_allow = _process_api_resource(api_resource_permissions, api_operation)
            if group_allow is not None:
                allowed = group_allow

            # Check the specific api operation permissions itself
            api_name_permissions = api_resource_permissions.get(api_name)
            if api_name_permissions:
                # Special permissions on a per-endpoint level are handled here
                endpoint_allow = validation_function(api_name_permissions, extra_data)
                if endpoint_allow is not None:
                    allowed = endpoint_allow

        return allowed

    def export_as_at_rest(self):
        return {
            "version": "1",
            "key_id": self.key_id,
            "key": self.key,
            "registration_time": self.registration_time,
            "root": self.root,
            "nickname": self.nickname,
            "permissions_document": self.permissions_document,
            "interchain": self.interchain,
        }


def _process_api_resource(permission_resource: Dict[str, Any], api_operation: str) -> Optional[bool]:
    """Helper method to check if the api action permission is in this API resource
    Args:
        permission_resource: The dictionary for this permission resource to check
        api_operation: The api_operation as defined from is_key_allowed
    Returns:
        Value of the resource permission if it exists, else None
    """
    if api_operation == "create":
        return permission_resource.get("allow_create")
    elif api_operation == "read":
        return permission_resource.get("allow_read")
    elif api_operation == "update":
        return permission_resource.get("allow_update")
    elif api_operation == "delete":
        return permission_resource.get("allow_delete")
    else:
        raise RuntimeError(f"'{api_operation}' is not a valid api_operation (must be one of create, read, update, delete)")

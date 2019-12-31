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

import functools
from typing import Callable, Any, TYPE_CHECKING

import flask

from dragonchain import exceptions
from dragonchain.lib import authorization

if TYPE_CHECKING:
    from dragonchain.lib.dto import api_key_model


class Authenticated(object):
    def __init__(self, api_resource: str, api_operation: str, api_name: str, interchain: bool = False):
        self.api_resource = api_resource
        self.api_operation = api_operation
        self.api_name = api_name
        self.interchain = interchain

    def __call__(self, authorized_func: Callable) -> Callable:
        """
        Decorator function calls check_auth and then performs the function,
        catching unauthorized requests to respond appropriately
        """

        @functools.wraps(authorized_func)
        def decorator(*args: Any, **kwargs: Any) -> Any:
            auth_key = self.check_auth()
            return authorized_func(*args, **kwargs, used_auth_key=auth_key)

        return decorator

    def check_auth(self) -> "api_key_model.APIKeyModel":
        """
        Checks for the validity of an authorization header string
        Raises exceptions.UnauthorizedException when the request is not authorized
        """
        auth_header = flask.request.headers.get("Authorization") or ""
        full_path = flask.request.full_path.rstrip("?")
        dcid = flask.request.headers.get("dragonchain")
        timestamp = flask.request.headers.get("timestamp")
        content_type = flask.request.headers.get("Content-Type")
        content = flask.request.data
        if not dcid:
            raise exceptions.UnauthorizedException("Missing Dragonchain ID in request header")
        if not timestamp:
            raise exceptions.UnauthorizedException("Missing timestamp in request header")
        if not content_type:
            content_type = ""
        if not content:
            content = b""
        return authorization.verify_request_authorization(
            authorization=auth_header,
            http_verb=flask.request.method,
            full_path=full_path,
            dcid=dcid,
            timestamp=timestamp,
            content_type=content_type,
            content=content,
            interchain=self.interchain,
            api_resource=self.api_resource,
            api_operation=self.api_operation,
            api_name=self.api_name,
        )

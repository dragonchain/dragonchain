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

from typing import Tuple, Dict

import fastjsonschema
import flask

from dragonchain.webserver.lib import api_keys
from dragonchain.webserver import helpers
from dragonchain.webserver import request_authorizer
from dragonchain.lib.dto import schema
from dragonchain import exceptions


_validate_api_key_creation_v1 = fastjsonschema.compile(schema.api_key_create_schema_v1)
_validate_api_key_update_v1 = fastjsonschema.compile(schema.api_key_update_schema_v1)


def apply_routes(app: flask.Flask):
    app.add_url_rule("/api-key", "create_api_key_v1", create_api_key_v1, methods=["POST"])
    app.add_url_rule("/v1/api-key", "create_api_key_v1", create_api_key_v1, methods=["POST"])
    app.add_url_rule("/api-key/<key_id>", "get_api_key_v1", get_api_key_v1, methods=["GET"])
    app.add_url_rule("/v1/api-key/<key_id>", "get_api_key_v1", get_api_key_v1, methods=["GET"])
    app.add_url_rule("/api-key", "list_api_keys_v1", list_api_keys_v1, methods=["GET"])
    app.add_url_rule("/v1/api-key", "list_api_keys_v1", list_api_keys_v1, methods=["GET"])
    app.add_url_rule("/api-key/<key_id>", "delete_api_key_v1", delete_api_key_v1, methods=["DELETE"])
    app.add_url_rule("/v1/api-key/<key_id>", "delete_api_key_v1", delete_api_key_v1, methods=["DELETE"])
    app.add_url_rule("/api-key/<key_id>", "update_api_key_v1", update_api_key_v1, methods=["PUT"])
    app.add_url_rule("/v1/api-key/<key_id>", "update_api_key_v1", update_api_key_v1, methods=["PUT"])


@request_authorizer.Authenticated(root_only=True)
@helpers.DisabledForLab
def create_api_key_v1() -> Tuple[str, int, Dict[str, str]]:
    nickname = ""
    if flask.request.is_json:
        body = flask.request.json
        try:
            _validate_api_key_creation_v1(body)
        except fastjsonschema.JsonSchemaException as e:
            raise exceptions.ValidationException(str(e))
        nickname = body.get("nickname") or ""

    return helpers.flask_http_response(201, api_keys.create_api_key_v1(nickname))


@request_authorizer.Authenticated()
@helpers.DisabledForLab
def get_api_key_v1(key_id: str) -> Tuple[str, int, Dict[str, str]]:
    if not key_id:
        raise exceptions.ValidationException("Invalid parameter: key_id")

    return helpers.flask_http_response(200, api_keys.get_api_key_v1(key_id))


@request_authorizer.Authenticated()
@helpers.DisabledForLab
def list_api_keys_v1() -> Tuple[str, int, Dict[str, str]]:
    return helpers.flask_http_response(200, api_keys.get_api_key_list_v1())


@request_authorizer.Authenticated(root_only=True)
@helpers.DisabledForLab
def delete_api_key_v1(key_id: str) -> Tuple[str, int, Dict[str, str]]:
    if not key_id:
        raise exceptions.ValidationException("Invalid parameter: key_id")

    api_keys.delete_api_key_v1(key_id=key_id)
    return helpers.flask_http_response(200, helpers.format_success(True))


@request_authorizer.Authenticated(root_only=True)
@helpers.DisabledForLab
def update_api_key_v1(key_id: str) -> Tuple[str, int, Dict[str, str]]:
    if not key_id:
        raise exceptions.ValidationException("Invalid parameter: key_id")

    if not flask.request.is_json:
        raise exceptions.BadRequest("Could not parse JSON")

    body = flask.request.json

    try:
        _validate_api_key_update_v1(body)
    except fastjsonschema.JsonSchemaException as e:
        raise exceptions.ValidationException(str(e))

    api_keys.update_api_key_v1(key_id, body["nickname"])
    return helpers.flask_http_response(200, helpers.format_success(True))

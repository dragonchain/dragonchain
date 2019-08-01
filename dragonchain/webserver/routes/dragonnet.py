from typing import Tuple, Dict, cast
import os

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

import flask
import fastjsonschema

from dragonchain.webserver.lib import dragonnet
from dragonchain.webserver import helpers
from dragonchain.webserver import request_authorizer
from dragonchain.lib.dto import schema
from dragonchain import exceptions

LEVEL = os.environ["LEVEL"]

_validate_interchain_auth_v1 = fastjsonschema.compile(schema.interchain_auth_registration_schema_v1)

if LEVEL == "2":
    _validate_broadcast_schema_v1 = fastjsonschema.compile(schema.l1_broadcast_schema_v1)
elif LEVEL == "3":
    _validate_broadcast_schema_v1 = fastjsonschema.compile(schema.l2_broadcast_schema_v1)
elif LEVEL == "4":
    _validate_broadcast_schema_v1 = fastjsonschema.compile(schema.l3_broadcast_schema_v1)
elif LEVEL == "5":
    _validate_broadcast_schema_v1 = fastjsonschema.compile(schema.l4_broadcast_schema_v1)


def apply_routes(app: flask.Flask):
    app.add_url_rule("/v1/interchain-auth-register", "dragonnet_auth_v1", dragonnet_auth_v1, methods=["POST"])
    if LEVEL == "1":
        app.add_url_rule("/v1/receipt", "receipt_v1", receipt_v1, methods=["POST"])
        app.add_url_rule("/v1/claim/<block_id>", "get_claim_v1", get_claim_v1, methods=["GET"])
    else:
        app.add_url_rule("/v1/enqueue", "enqueue_v1", enqueue_v1, methods=["POST"])


@request_authorizer.Authenticated(interchain=True)
def receipt_v1() -> Tuple[str, int, Dict[str, str]]:
    if not flask.request.is_json:
        raise exceptions.BadRequest("Could not parse JSON")

    content = flask.request.json

    try:
        dragonnet.process_receipt_v1(content)
    except NotImplementedError as e:
        raise exceptions.BadRequest(str(e))
    return helpers.flask_http_response(200, helpers.format_success(True))


@request_authorizer.Authenticated(interchain=True)
def get_claim_v1(block_id: str) -> Tuple[str, int, Dict[str, str]]:
    if not block_id:
        raise exceptions.BadRequest("block_id is required")

    return helpers.flask_http_response(200, dragonnet.get_local_claim_v1(block_id))


@request_authorizer.Authenticated(interchain=True)
def enqueue_v1() -> Tuple[str, int, Dict[str, str]]:
    if not flask.request.is_json:
        raise exceptions.BadRequest("Could not parse JSON")

    content = flask.request.json
    deadline = int(cast(str, flask.request.headers.get("deadline"))) if flask.request.headers.get("deadline") else 30

    try:
        _validate_broadcast_schema_v1(content)
    except fastjsonschema.JsonSchemaException:
        raise exceptions.ValidationException("Input did not match JSON schema")

    dragonnet.enqueue_item_for_verification_v1(content, deadline)
    return helpers.flask_http_response(200, helpers.format_success(True))


def dragonnet_auth_v1() -> Tuple[str, int, Dict[str, str]]:
    """
    Create a new DragonNet interchain communication key pair with the requester (unauthenticated by design)
    """
    if not flask.request.is_json:
        raise exceptions.BadRequest("Could not parse JSON")

    body = flask.request.json

    try:
        _validate_interchain_auth_v1(body)
    except fastjsonschema.JsonSchemaException:
        raise exceptions.ValidationException("Request body did not match JSON schema")

    dragonnet.register_interchain_auth_v1(body)
    return helpers.flask_http_response(201, helpers.format_success(True))

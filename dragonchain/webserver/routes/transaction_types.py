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

import flask
import fastjsonschema

from dragonchain.webserver.lib import transaction_types
from dragonchain.webserver import helpers
from dragonchain.webserver import request_authorizer
from dragonchain.lib.dto import schema
from dragonchain import exceptions


_validate_create_txn_type_v1 = fastjsonschema.compile(schema.new_transaction_type_register_request_schema_v1)


def apply_routes(app: flask.Flask):
    # Register
    app.add_url_rule("/transaction-type", "register_transaction_type_v1", register_transaction_type_v1, methods=["POST"])
    app.add_url_rule("/v1/transaction-type", "register_transaction_type_v1", register_transaction_type_v1, methods=["POST"])
    # Delete
    app.add_url_rule("/transaction-type/<txn_type>", "delete_transaction_type_v1", delete_transaction_type_v1, methods=["DELETE"])
    app.add_url_rule("/v1/transaction-type/<txn_type>", "delete_transaction_type_v1", delete_transaction_type_v1, methods=["DELETE"])
    # Get
    app.add_url_rule("/transaction-type/<txn_type>", "get_transaction_type_v1", get_transaction_type_v1, methods=["GET"])
    app.add_url_rule("/v1/transaction-type/<txn_type>", "get_transaction_type_v1", get_transaction_type_v1, methods=["GET"])
    # List
    app.add_url_rule("/transaction-types", "list_transaction_types_v1", list_transaction_types_v1, methods=["GET"])
    app.add_url_rule("/v1/transaction-types", "list_transaction_types_v1", list_transaction_types_v1, methods=["GET"])


@request_authorizer.Authenticated()
@helpers.DisabledForLab
def register_transaction_type_v1() -> Tuple[str, int, Dict[str, str]]:
    if not flask.request.is_json:
        raise exceptions.BadRequest("Could not parse JSON")

    content = flask.request.json

    try:
        _validate_create_txn_type_v1(content)
        if content.get("custom_indexes"):
            helpers.verify_custom_indexes_options(content["custom_indexes"])
    except fastjsonschema.JsonSchemaException as e:
        raise exceptions.ValidationException(str(e))

    transaction_types.register_transaction_type_v1(content)
    return helpers.flask_http_response(200, helpers.format_success(True))


@request_authorizer.Authenticated()
@helpers.DisabledForLab
def delete_transaction_type_v1(txn_type: str) -> Tuple[str, int, Dict[str, str]]:
    if not txn_type:
        raise exceptions.ValidationException("Invalid parameter: txn_type")

    transaction_types.delete_transaction_type_v1(txn_type)
    return helpers.flask_http_response(200, helpers.format_success(True))


@request_authorizer.Authenticated()
def list_transaction_types_v1() -> Tuple[str, int, Dict[str, str]]:
    return helpers.flask_http_response(200, transaction_types.list_registered_transaction_types_v1())


@request_authorizer.Authenticated()
def get_transaction_type_v1(txn_type: str) -> Tuple[str, int, Dict[str, str]]:
    if not txn_type:
        raise exceptions.ValidationException("Invalid parameter: txn_type")

    return helpers.flask_http_response(200, transaction_types.get_transaction_type_v1(txn_type))

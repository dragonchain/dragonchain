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

from typing import Tuple, Dict

import fastjsonschema
import flask

from dragonchain.webserver.lib import transactions
from dragonchain.webserver import helpers
from dragonchain.webserver import request_authorizer
from dragonchain.lib.dto import schema
from dragonchain import exceptions

_validate_txn_create_v1 = fastjsonschema.compile(schema.transaction_create_schema_v1)
_validate_bulk_txn_create_v1 = fastjsonschema.compile(schema.bulk_transaction_create_schema_v1)


def apply_routes(app: flask.Flask):
    app.add_url_rule("/transaction", "post_transaction_v1", post_transaction_v1, methods=["POST"])
    app.add_url_rule("/v1/transaction", "post_transaction_v1", post_transaction_v1, methods=["POST"])
    app.add_url_rule("/transaction_bulk", "post_transaction_bulk_v1", post_transaction_bulk_v1, methods=["POST"])
    app.add_url_rule("/v1/transaction_bulk", "post_transaction_bulk_v1", post_transaction_bulk_v1, methods=["POST"])
    app.add_url_rule("/transaction", "query_transaction_v1", query_transaction_v1, methods=["GET"])
    app.add_url_rule("/v1/transaction", "query_transaction_v1", query_transaction_v1, methods=["GET"])
    app.add_url_rule("/transaction/<transaction_id>", "get_transaction_v1", get_transaction_v1, methods=["GET"])
    app.add_url_rule("/v1/transaction/<transaction_id>", "get_transaction_v1", get_transaction_v1, methods=["GET"])


@request_authorizer.Authenticated(api_resource="transactions", api_operation="create", api_name="create_transaction")
def post_transaction_v1(**kwargs) -> Tuple[str, int, Dict[str, str]]:
    if not flask.request.is_json:
        raise exceptions.BadRequest("Could not parse JSON")

    txn = flask.request.json

    try:
        _validate_txn_create_v1(txn)
    except fastjsonschema.JsonSchemaException as e:
        raise exceptions.ValidationException(str(e))

    return helpers.flask_http_response(
        201, transactions.submit_transaction_v1(txn, flask.request.headers.get("X-Callback-URL"), api_key=kwargs["used_auth_key"])
    )


@request_authorizer.Authenticated(api_resource="transactions", api_operation="create", api_name="create_transaction")
def post_transaction_bulk_v1(**kwargs) -> Tuple[str, int, Dict[str, str]]:
    """
    Enqueue bulk transactions to be processed
    """
    if not flask.request.is_json:
        raise exceptions.BadRequest("Could not parse JSON")

    content = flask.request.json

    try:
        _validate_bulk_txn_create_v1(content)
    except fastjsonschema.JsonSchemaException as e:
        raise exceptions.ValidationException(str(e))

    response = transactions.submit_bulk_transaction_v1(content, api_key=kwargs["used_auth_key"])
    if not response["201"]:
        return helpers.flask_http_response(400, response)
    return helpers.flask_http_response(207, response)


@request_authorizer.Authenticated(api_resource="transactions", api_operation="read", api_name="query_transactions")
def query_transaction_v1(**kwargs) -> Tuple[str, int, Dict[str, str]]:
    params = helpers.parse_query_parameters(flask.request.args.to_dict())
    if params.get("transaction_type"):
        should_parse = flask.request.headers.get("Parse-Payload") != "false"
        return helpers.flask_http_response(200, transactions.query_transactions_v1(params, should_parse))
    raise exceptions.ValidationException("User input must specify transaction type to query")


@request_authorizer.Authenticated(api_resource="transactions", api_operation="read", api_name="get_transaction")
def get_transaction_v1(transaction_id: str, **kwargs) -> Tuple[str, int, Dict[str, str]]:
    if not transaction_id:
        raise exceptions.BadRequest("Parameter 'transaction_id' is required")
    should_parse = flask.request.headers.get("Parse-Payload") != "false"
    return helpers.flask_http_response(200, transactions.get_transaction_v1(transaction_id, should_parse))

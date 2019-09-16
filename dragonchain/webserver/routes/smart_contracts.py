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

from dragonchain.webserver.lib import smart_contracts
from dragonchain.webserver import helpers
from dragonchain.webserver import request_authorizer
from dragonchain.lib.dto import schema
from dragonchain import exceptions

_validate_sc_create_v1 = fastjsonschema.compile(schema.smart_contract_create_schema_v1)
_validate_sc_update_v1 = fastjsonschema.compile(schema.smart_contract_update_schema_v1)


def apply_routes(app: flask.Flask):
    app.add_url_rule("/contract", "list_contract_v1", list_contract_v1, methods=["GET"])
    app.add_url_rule("/v1/contract", "list_contract_v1", list_contract_v1, methods=["GET"])
    app.add_url_rule("/contract/<contract_id>", "get_contract_by_id_v1", get_contract_by_id_v1, methods=["GET"])
    app.add_url_rule("/v1/contract/<contract_id>", "get_contract_by_id_v1", get_contract_by_id_v1, methods=["GET"])
    app.add_url_rule("/contract/logs/<contract_id>", "get_smart_contract_logs_v1", get_smart_contract_logs_v1, methods=["GET"])
    app.add_url_rule("/v1/contract/logs/<contract_id>", "get_smart_contract_logs_v1", get_smart_contract_logs_v1, methods=["GET"])
    app.add_url_rule("/contract/txn_type/<txn_type>", "get_contract_by_txn_type_v1", get_contract_by_txn_type_v1, methods=["GET"])
    app.add_url_rule("/v1/contract/txn_type/<txn_type>", "get_contract_by_txn_type_v1", get_contract_by_txn_type_v1, methods=["GET"])
    app.add_url_rule("/contract", "post_contract_v1", post_contract_v1, methods=["POST"])
    app.add_url_rule("/v1/contract", "post_contract_v1", post_contract_v1, methods=["POST"])
    app.add_url_rule("/contract/<contract_id>", "update_contract_v1", update_contract_v1, methods=["PUT"])
    app.add_url_rule("/v1/contract/<contract_id>", "update_contract_v1", update_contract_v1, methods=["PUT"])
    app.add_url_rule("/contract/<contract_id>", "delete_contract_v1", delete_contract_v1, methods=["DELETE"])
    app.add_url_rule("/v1/contract/<contract_id>", "delete_contract_v1", delete_contract_v1, methods=["DELETE"])
    app.add_url_rule("/get/<path:key>", "get_sc_heap_v1", get_sc_heap_v1, methods=["GET"])  # :path allows / in key variable
    app.add_url_rule("/v1/get/<path:key>", "get_sc_heap_v1", get_sc_heap_v1, methods=["GET"])  # :path allows / in key variable
    app.add_url_rule("/list/<path:prefix_key>", "list_sc_heap_v1", list_sc_heap_v1, methods=["GET"])  # :path allows / in key variable
    app.add_url_rule("/v1/list/<path:prefix_key>", "list_sc_heap_v1", list_sc_heap_v1, methods=["GET"])  # :path allows / in key variable


@request_authorizer.Authenticated()
def get_contract_by_id_v1(contract_id: str) -> Tuple[str, int, Dict[str, str]]:
    return helpers.flask_http_response(200, smart_contracts.get_by_id_v1(contract_id))


@request_authorizer.Authenticated()
def get_contract_by_txn_type_v1(txn_type: str) -> Tuple[str, int, Dict[str, str]]:
    return helpers.flask_http_response(200, smart_contracts.get_by_txn_type_v1(txn_type))


@request_authorizer.Authenticated()
def list_contract_v1() -> Tuple[str, int, Dict[str, str]]:
    return helpers.flask_http_response(200, smart_contracts.list_contracts_v1())


@request_authorizer.Authenticated()
def get_smart_contract_logs_v1(contract_id: str) -> Tuple[str, int, Dict[str, str]]:
    since = flask.request.args.get("since")
    tail = flask.request.args.get("tail")
    return helpers.flask_http_response(200, smart_contracts.get_logs_v1(contract_id, since, tail))


@request_authorizer.Authenticated()
@helpers.DisabledForLab
def post_contract_v1() -> Tuple[str, int, Dict[str, str]]:
    if not flask.request.is_json:
        raise exceptions.BadRequest("Could not parse JSON")

    contract = flask.request.json

    try:
        _validate_sc_create_v1(contract)
        if contract.get("custom_indexes"):
            helpers.verify_custom_indexes_options(contract.get("custom_indexes"))
    except fastjsonschema.JsonSchemaException:
        raise exceptions.ValidationException("User input did not match JSON schema")

    return helpers.flask_http_response(202, smart_contracts.create_contract_v1(contract))


@request_authorizer.Authenticated()
@helpers.DisabledForLab
def update_contract_v1(contract_id: str) -> Tuple[str, int, Dict[str, str]]:
    if not flask.request.is_json:
        raise exceptions.BadRequest("Could not parse JSON")

    update = flask.request.json

    try:
        _validate_sc_update_v1(update)
    except fastjsonschema.JsonSchemaException:
        raise exceptions.ValidationException("User input did not match JSON schema")

    return helpers.flask_http_response(202, smart_contracts.update_contract_v1(contract_id, update))


@request_authorizer.Authenticated()
@helpers.DisabledForLab
def delete_contract_v1(contract_id: str) -> Tuple[str, int, Dict[str, str]]:
    smart_contracts.delete_contract_v1(contract_id)
    return helpers.flask_http_response(202, helpers.format_success(True))


@request_authorizer.Authenticated()
def get_sc_heap_v1(key: str) -> Tuple[str, int]:
    """
    /v1/get/<contract_id>/HEAP/<key>
    method = GET
    path = '/' seperate string where the left side is the contract_id
            and the right side is the object key in the heap
    Get a value from the smart contract heap in storage
    """
    initial_index = key.find("/")
    if initial_index == -1:
        raise exceptions.BadRequest("Path must look like /v1/get/<contract_id>/<object_key>")
    contract_id = key[:initial_index]
    path = key[initial_index:]
    return (
        smart_contracts.heap_get_v1(contract_id, path),
        200,
    )  # Explicitly not using helpers.flask_http_response, because response isn't necessarily JSON


@request_authorizer.Authenticated()
def list_sc_heap_v1(prefix_key: str) -> Tuple[str, int, Dict[str, str]]:
    """
    /v1/list/<prefix_key>
    method = GET
    path = '/' seperate string where the left side is the contract_id
            and the right side is an optional object key in the heap

            i.e. /v1/list/currency_contract/folder_in_heap (to search the folder_in_heap for a the currency_contract SC)
            i.e. /v1/list/a_contract/ (to list at the root of the heap for the a_contract SC)
    Get an array of keys from the smart contract heap in storage
    List storage keys under a prefix
    """
    initial_index = prefix_key.find("/")
    if initial_index == -1:
        raise exceptions.BadRequest(
            "Path must look like /v1/list/<contract_id>/<object_folder> or /v1/list/<contract_id>/ to search the root of the heap"
        )
    contract_id = prefix_key[:initial_index]
    path = prefix_key[initial_index:]
    return helpers.flask_http_response(200, smart_contracts.heap_list_v1(contract_id, path))

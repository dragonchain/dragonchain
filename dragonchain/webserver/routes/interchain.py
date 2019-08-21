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

import os
from typing import Tuple, Dict

import flask
import fastjsonschema

from dragonchain.webserver.lib import interchain
from dragonchain.webserver import helpers
from dragonchain.webserver import request_authorizer
from dragonchain.lib.dto import schema
from dragonchain import exceptions

LEVEL = os.environ["LEVEL"]

_validate_bitcoin_network_create_v1 = fastjsonschema.compile(schema.create_bitcoin_interchain_schema_v1)
_validate_bitcoin_network_update_v1 = fastjsonschema.compile(schema.update_bitcoin_interchain_schema_v1)
_validate_bitcoin_transaction_v1 = fastjsonschema.compile(schema.btc_transaction_schema_v1)

_validate_ethereum_network_create_v1 = fastjsonschema.compile(schema.create_ethereum_interchain_schema_v1)
_validate_ethereum_network_update_v1 = fastjsonschema.compile(schema.update_ethereum_interchain_schema_v1)
_validate_ethereum_transaction_v1 = fastjsonschema.compile(schema.eth_transaction_schema_v1)

_validate_set_default_interchain_v1 = fastjsonschema.compile(schema.set_default_interchain_schema_v1)


def apply_routes(app: flask.Flask):
    # Create Interchain Network
    app.add_url_rule("/v1/interchains/bitcoin", "create_bitcoin_interchain_v1", create_bitcoin_interchain_v1, methods=["POST"])
    app.add_url_rule("/v1/interchains/ethereum", "create_ethereum_interchain_v1", create_ethereum_interchain_v1, methods=["POST"])
    # Update Interchain Network
    app.add_url_rule("/v1/interchains/bitcoin/<name>", "update_bitcoin_interchain_v1", update_bitcoin_interchain_v1, methods=["PATCH"])
    app.add_url_rule("/v1/interchains/ethereum/<name>", "update_ethereum_interchain_v1", update_ethereum_interchain_v1, methods=["PATCH"])
    # Create Interchain Transaction
    app.add_url_rule("/v1/interchains/bitcoin/<name>/transaction", "create_bitcoin_transaction_v1", create_bitcoin_transaction_v1, methods=["POST"])
    app.add_url_rule(
        "/v1/interchains/ethereum/<name>/transaction", "create_ethereum_transaction_v1", create_ethereum_transaction_v1, methods=["POST"]
    )
    # List
    app.add_url_rule("/v1/interchains/<blockchain>", "list_interchains_v1", list_interchains_v1, methods=["GET"])
    # Get
    app.add_url_rule("/v1/interchains/<blockchain>/<name>", "get_interchain_v1", get_interchain_v1, methods=["GET"])
    # Delete
    app.add_url_rule("/v1/interchains/<blockchain>/<name>", "delete_interchain_v1", delete_interchain_v1, methods=["DELETE"])
    # Defaults for L5
    if LEVEL == "5":
        app.add_url_rule("/v1/interchains/default", "set_default_network_v1", set_default_network_v1, methods=["POST"])
        app.add_url_rule("/v1/interchains/default", "get_default_network_v1", get_default_network_v1, methods=["GET"])

    # Kept for backwards compatibility. Will not work with new chains
    app.add_url_rule("/public-blockchain-address", "public_blockchain_address_v1", public_blockchain_address_v1, methods=["GET"])
    app.add_url_rule("/v1/public-blockchain-address", "public_blockchain_address_v1", public_blockchain_address_v1, methods=["GET"])
    app.add_url_rule("/public-blockchain-transaction", "public_blockchain_transaction_v1", public_blockchain_transaction_v1, methods=["POST"])
    app.add_url_rule("/v1/public-blockchain-transaction", "public_blockchain_transaction_v1", public_blockchain_transaction_v1, methods=["POST"])


@request_authorizer.Authenticated()
def create_bitcoin_interchain_v1() -> Tuple[str, int, Dict[str, str]]:
    if not flask.request.is_json:
        raise exceptions.BadRequest("Could not parse JSON")
    data = flask.request.json
    try:
        _validate_bitcoin_network_create_v1(data)
    except fastjsonschema.JsonSchemaException:
        raise exceptions.ValidationException("User input did not match JSON schema")

    return helpers.flask_http_response(201, interchain.create_bitcoin_interchain_v1(data))


@request_authorizer.Authenticated()
def create_ethereum_interchain_v1() -> Tuple[str, int, Dict[str, str]]:
    if not flask.request.is_json:
        raise exceptions.BadRequest("Could not parse JSON")
    data = flask.request.json
    try:
        _validate_ethereum_network_create_v1(data)
    except fastjsonschema.JsonSchemaException:
        raise exceptions.ValidationException("User input did not match JSON schema")

    return helpers.flask_http_response(201, interchain.create_ethereum_interchain_v1(data))


@request_authorizer.Authenticated()
def update_bitcoin_interchain_v1(name: str) -> Tuple[str, int, Dict[str, str]]:
    if not flask.request.is_json:
        raise exceptions.BadRequest("Could not parse JSON")
    data = flask.request.json
    try:
        _validate_bitcoin_network_update_v1(data)
    except fastjsonschema.JsonSchemaException:
        raise exceptions.ValidationException("User input did not match JSON schema")

    return helpers.flask_http_response(200, interchain.update_bitcoin_interchain_v1(name, data))


@request_authorizer.Authenticated()
def update_ethereum_interchain_v1(name: str) -> Tuple[str, int, Dict[str, str]]:
    if not flask.request.is_json:
        raise exceptions.BadRequest("Could not parse JSON")
    data = flask.request.json
    try:
        _validate_ethereum_network_update_v1(data)
    except fastjsonschema.JsonSchemaException:
        raise exceptions.ValidationException("User input did not match JSON schema")

    return helpers.flask_http_response(200, interchain.update_ethereum_interchain_v1(name, data))


@request_authorizer.Authenticated()
def create_bitcoin_transaction_v1(name: str) -> Tuple[str, int, Dict[str, str]]:
    if not flask.request.is_json:
        raise exceptions.BadRequest("Could not parse JSON")
    data = flask.request.json
    try:
        _validate_bitcoin_transaction_v1(data)
    except fastjsonschema.JsonSchemaException:
        raise exceptions.ValidationException("User input did not match JSON schema")

    return helpers.flask_http_response(200, interchain.sign_interchain_transaction_v1("bitcoin", name, data))


@request_authorizer.Authenticated()
def create_ethereum_transaction_v1(name: str) -> Tuple[str, int, Dict[str, str]]:
    if not flask.request.is_json:
        raise exceptions.BadRequest("Could not parse JSON")
    data = flask.request.json
    try:
        _validate_ethereum_transaction_v1(data)
    except fastjsonschema.JsonSchemaException:
        raise exceptions.ValidationException("User input did not match JSON schema")

    return helpers.flask_http_response(200, interchain.sign_interchain_transaction_v1("ethereum", name, data))


@request_authorizer.Authenticated()
def list_interchains_v1(blockchain: str) -> Tuple[str, int, Dict[str, str]]:
    return helpers.flask_http_response(200, interchain.list_interchain_v1(blockchain))


@request_authorizer.Authenticated()
def get_interchain_v1(blockchain: str, name: str) -> Tuple[str, int, Dict[str, str]]:
    return helpers.flask_http_response(200, interchain.get_interchain_v1(blockchain, name))


@request_authorizer.Authenticated()
def delete_interchain_v1(blockchain: str, name: str) -> Tuple[str, int, Dict[str, str]]:
    interchain.delete_interchain_v1(blockchain, name)
    return helpers.flask_http_response(200, helpers.format_success(True))


@request_authorizer.Authenticated()
def set_default_network_v1() -> Tuple[str, int, Dict[str, str]]:
    if not flask.request.is_json:
        raise exceptions.BadRequest("Could not parse JSON")
    data = flask.request.json
    try:
        _validate_set_default_interchain_v1(data)
    except fastjsonschema.JsonSchemaException:
        raise exceptions.ValidationException("User input did not match JSON schema")

    return helpers.flask_http_response(200, interchain.set_default_interchain_v1(data["blockchain"], data["name"]))


@request_authorizer.Authenticated()
def get_default_network_v1() -> Tuple[str, int, Dict[str, str]]:
    return helpers.flask_http_response(200, interchain.get_default_interchain_v1())


# Backwards compatibility routes. Will only work on old chains, not newly created ones


@request_authorizer.Authenticated()
def public_blockchain_address_v1() -> Tuple[str, int, Dict[str, str]]:
    return helpers.flask_http_response(200, interchain.legacy_get_blockchain_addresses_v1())


@request_authorizer.Authenticated()
def public_blockchain_transaction_v1() -> Tuple[str, int, Dict[str, str]]:
    if not flask.request.is_json:
        raise exceptions.BadRequest("Could not parse JSON")

    data = flask.request.json

    if not data.get("network"):
        raise exceptions.ValidationException("Invalid parameter: network")
    try:
        if data["network"] in ["BTC_MAINNET", "BTC_TESTNET3"]:
            _validate_bitcoin_transaction_v1(data.get("transaction"))
        elif data["network"] in ["ETH_MAINNET", "ETH_ROPSTEN", "ETC_MAINNET", "ETC_MORDEN"]:
            _validate_ethereum_transaction_v1(data.get("transaction"))
        else:
            raise exceptions.ValidationException("User input did not match JSON schema")
    except fastjsonschema.JsonSchemaException:
        raise exceptions.ValidationException("User input did not match JSON schema")

    return helpers.flask_http_response(200, interchain.legacy_sign_blockchain_transaction_v1(data["network"], data["transaction"]))

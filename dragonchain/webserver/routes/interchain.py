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

from dragonchain.webserver.lib import interchain
from dragonchain.webserver import helpers
from dragonchain.webserver import request_authorizer
from dragonchain.lib.dto import schema
from dragonchain import exceptions

_validate_bitcoin_transaction_v1 = fastjsonschema.compile(schema.get_public_blockchain_transaction_schema_v1("BTC"))
_validate_ethereum_transaction_v1 = fastjsonschema.compile(schema.get_public_blockchain_transaction_schema_v1("ETH"))


def apply_routes(app: flask.Flask):
    app.add_url_rule("/public-blockchain-address", "public_blockchain_address_v1", public_blockchain_address_v1, methods=["GET"])
    app.add_url_rule("/v1/public-blockchain-address", "public_blockchain_address_v1", public_blockchain_address_v1, methods=["GET"])
    app.add_url_rule("/public-blockchain-transaction", "public_blockchain_transaction_v1", public_blockchain_transaction_v1, methods=["POST"])
    app.add_url_rule("/v1/public-blockchain-transaction", "public_blockchain_transaction_v1", public_blockchain_transaction_v1, methods=["POST"])


@request_authorizer.Authenticated()
def public_blockchain_address_v1() -> Tuple[str, int, Dict[str, str]]:
    return helpers.flask_http_response(200, interchain.get_blockchain_addresses_v1())


@request_authorizer.Authenticated()
def public_blockchain_transaction_v1() -> Tuple[str, int, Dict[str, str]]:
    if not flask.request.is_json:
        raise exceptions.BadRequest("Could not parse JSON")

    data = flask.request.json

    if not data.get("network"):
        raise exceptions.ValidationException("Invalid parameter: network")
    try:
        if data["network"] in ["BTC_MAINNET", "BTC_TESTNET3"]:
            _validate_bitcoin_transaction_v1(data)
        elif data["network"] in ["ETH_MAINNET", "ETH_ROPSTEN", "ETC_MAINNET", "ETC_MORDEN"]:
            _validate_ethereum_transaction_v1(data)
        else:
            raise exceptions.ValidationException("User input did not match JSON schema")
    except fastjsonschema.JsonSchemaException:
        raise exceptions.ValidationException("User input did not match JSON schema")

    return helpers.flask_http_response(200, interchain.sign_blockchain_transaction_v1(data["network"], data["transaction"]))

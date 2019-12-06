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

from typing import Tuple, Dict, Optional

import flask

from dragonchain.webserver import helpers
from dragonchain.webserver.lib import blocks
from dragonchain.webserver import request_authorizer
from dragonchain.lib.database import redisearch


def apply_routes(app: flask.Flask):
    if redisearch.ENABLED:
        app.add_url_rule("/block", "query_blocks_v1", query_blocks_v1, methods=["GET"])
        app.add_url_rule("/v1/block", "query_blocks_v1", query_blocks_v1, methods=["GET"])
    app.add_url_rule("/block/<block_id>", "get_block_v1", get_block_v1, methods=["GET"])
    app.add_url_rule("/v1/block/<block_id>", "get_block_v1", get_block_v1, methods=["GET"])


@request_authorizer.Authenticated(api_resource="blocks", api_operation="read", api_name="get_block")
def get_block_v1(block_id: str, **kwargs) -> Tuple[str, int, Dict[str, str]]:
    should_parse = bool(flask.request.headers.get("Parse-Payload"))
    return helpers.flask_http_response(200, blocks.get_block_by_id_v1(block_id, should_parse))


@request_authorizer.Authenticated(api_resource="blocks", api_operation="read", api_name="query_blocks")
def query_blocks_v1(block_id: Optional[str] = None, **kwargs) -> Tuple[str, int, Dict[str, str]]:
    params = helpers.parse_query_parameters(flask.request.args.to_dict())
    should_parse = bool(flask.request.headers.get("Parse-Payload"))
    return helpers.flask_http_response(200, blocks.query_blocks_v1(params, should_parse))

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

from dragonchain.webserver import helpers
from dragonchain.webserver.lib import misc
from dragonchain.webserver import request_authorizer


def apply_routes(app: flask.Flask):
    app.add_url_rule("/health", "health_check", health_check, methods=["GET"])
    app.add_url_rule("/status", "get_status_v1", get_status_v1, methods=["GET"])
    app.add_url_rule("/v1/status", "get_status_v1", get_status_v1, methods=["GET"])


def health_check() -> Tuple[str, int]:
    """
    Simple health check endpoint to make sure that the webserver is running and able to be hit externally (not authenticated)
    """
    return "OK\n", 200  # Explicitly not HTTP response because this isn't JSON


@request_authorizer.Authenticated(api_resource="misc", api_operation="read", api_name="get_status")
def get_status_v1(**kwargs) -> Tuple[str, int, Dict[str, str]]:
    """
    Return status data about a chain
    """
    return helpers.flask_http_response(200, misc.get_v1_status())

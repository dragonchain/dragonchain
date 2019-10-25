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

from typing import TYPE_CHECKING
import os

from dragonchain.webserver import helpers
from dragonchain.webserver.routes import api_keys
from dragonchain.webserver.routes import blocks
from dragonchain.webserver.routes import misc
from dragonchain.webserver.routes import dragonnet

LEVEL = os.environ["LEVEL"]

if LEVEL == "1":
    from dragonchain.webserver.routes import verifications
    from dragonchain.webserver.routes import smart_contracts
    from dragonchain.webserver.routes import transaction_types
    from dragonchain.webserver.routes import transactions

if LEVEL == "1" or LEVEL == "5":
    from dragonchain.webserver.routes import interchain

if TYPE_CHECKING:
    import flask


def route(app: "flask.Flask"):
    # All Levels
    api_keys.apply_routes(app)
    blocks.apply_routes(app)
    misc.apply_routes(app)
    dragonnet.apply_routes(app)

    if LEVEL == "1":
        verifications.apply_routes(app)
        smart_contracts.apply_routes(app)
        transaction_types.apply_routes(app)
        transactions.apply_routes(app)

    if LEVEL == "1" or LEVEL == "5":
        interchain.apply_routes(app)

    # Error Handler
    app.register_error_handler(Exception, helpers.webserver_error_handler)

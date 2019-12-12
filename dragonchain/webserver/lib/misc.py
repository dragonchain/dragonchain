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
from typing import Dict, Any

from dragonchain import logger
from dragonchain.lib import matchmaking
from dragonchain.lib import keys
from dragonchain.lib.database import redisearch

_log = logger.get_logger()


def get_v1_status() -> Dict[str, Any]:
    matchmaking_data = matchmaking.get_matchmaking_config()
    response: Dict[str, Any] = {
        "id": str(keys.get_public_id()),
        "level": int(matchmaking_data["level"]),
        "url": str(matchmaking_data["url"]),
        "hashAlgo": str(matchmaking_data["hashAlgo"]),
        "scheme": str(matchmaking_data["scheme"]),
        "version": str(matchmaking_data["version"]),
        "encryptionAlgo": str(matchmaking_data["encryptionAlgo"]),
        "indexingEnabled": redisearch.ENABLED,
    }
    # Return extra data if level 5
    if os.environ["LEVEL"] == "5":
        response["funded"] = bool(matchmaking_data["funded"])
        response["broadcastInterval"] = float(matchmaking_data["broadcastInterval"])
        response["network"] = str(matchmaking_data.get("network"))
        response["interchainWallet"] = str(matchmaking_data.get("interchainWallet"))
    return response

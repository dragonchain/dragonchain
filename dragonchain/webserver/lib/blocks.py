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

import json
from typing import Dict, Any, TYPE_CHECKING

import redis

from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib.dto import schema
from dragonchain.lib.database import elasticsearch
from dragonchain.lib.interfaces import storage

if TYPE_CHECKING:
    from dragonchain.lib.types import ESSearch  # noqa: F401

_log = logger.get_logger()


def query_blocks_v1(params: Dict[str, Any], parse: bool = False) -> "ESSearch":
    """Returns block matching block id, with query parameters accepted.
    Args:
        block_id: string Block id to search for.
        params: Dictionary of redisearch query options
        parse: whether or not we should parse contents
    """
    try:
        query_result = elasticsearch.search(
            index=elasticsearch.Indexes.block.value,
            q=params["q"],
            query=params["query"],
            offset=params.get("offset"),
            limit=params.get("limit"),
            sort=params.get("sort"),
        )
    except redis.exceptions.ResponseError as e:
        # Detect if this is a syntax error; if so, throw it back as a 400 with the message
        if str(e).startswith("Syntax error"):
            raise exceptions.BadRequest(str(e))
        else:
            raise
    result: "ESSearch" = {"total": query_result["total"], "results": []}
    if params.get("id_only"):
        result["results"] = [x.id for x in query_result["results"]]
    else:
        blocks = []
        for block in query_result["results"]:
            blocks.append(get_block_by_id_v1(block.id, parse))
        result["results"] = blocks
    return result


def get_block_by_id_v1(block_id: str, parse: bool = False) -> Dict[str, Any]:
    """Searches for a block by a specific block ID
    Args:
        block_id: The block id to get
        parse: whether or not to parse the result automatically
    """
    raw_block = storage.get_json_from_object(f"BLOCK/{block_id}")
    if parse and raw_block["dcrn"] == schema.DCRN.Block_L1_At_Rest.value:
        for index, transaction in enumerate(raw_block["transactions"]):
            raw_block["transactions"][index] = json.loads(transaction)
    return raw_block

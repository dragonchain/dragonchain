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

from typing import Optional, Dict, Any, TYPE_CHECKING

from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib.dao import block_dao
from dragonchain.lib.database import elasticsearch

if TYPE_CHECKING:
    from dragonchain.lib.types import ESSearch

_log = logger.get_logger()


def query_blocks_v1(params: Optional[dict], parse: bool) -> "ESSearch":
    """Returns block matching block id, with query parameters accepted.
    Args:
        block_id: string Block id to search for.
        params: string Lucene syntax acceptable query string for Elastic searching.
        parse: whether or not we should parse contents
    """
    if params:
        query_params = params.get("q") or "*"  # default to returning all results (limit 10 by default)
        sort_param = params.get("sort") or "block_id:desc"
        limit_param = params.get("limit") or None
        offset_param = params.get("offset") or None
        _log.info(f"[BLOCK] QUERY STRING PARAMS FOUND: {query_params}")
        return elasticsearch.search("BLOCK", q=query_params, sort=sort_param, limit=limit_param, offset=offset_param, should_parse=parse)
    else:
        return elasticsearch.search("BLOCK", q="*", sort="block_id:desc", should_parse=parse)


def get_block_by_id_v1(block_id: str, parse: bool) -> Dict[str, Any]:
    """Searches for a block by a specific block ID
    Args:
        block_id: The block id to get
        parse: whether or not to parse the result automatically
    """
    results = elasticsearch.search(folder=block_dao.FOLDER, query={"query": {"match_phrase": {"block_id": block_id}}}, should_parse=parse)["results"]

    if len(results) > 0:
        return results[0]

    raise exceptions.NotFound(f"Block {block_id} could not be found.")

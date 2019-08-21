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

from typing import Dict, Union, List, Any, Optional

from dragonchain.broadcast_processor import broadcast_functions
from dragonchain.lib.interfaces import storage
from dragonchain.lib import matchmaking
from dragonchain import exceptions
from dragonchain import logger

_log = logger.get_logger()


def get_pending_verifications_v1(block_id: str) -> Dict[str, List[str]]:
    """Get any scheduled pending verifications"""
    claim_check = matchmaking.get_claim_check(block_id)
    verifications = broadcast_functions.get_all_verifications_for_block_sync(block_id)
    scheduled_l2 = set(claim_check["validations"]["l2"].keys())
    scheduled_l3 = set(claim_check["validations"]["l3"].keys())
    scheduled_l4 = set(claim_check["validations"]["l4"].keys())
    scheduled_l5 = set(claim_check["validations"]["l5"].keys())
    # Get only the differences (scheduled, but not received) chains
    return {
        "2": list(scheduled_l2.difference(verifications[0])),
        "3": list(scheduled_l3.difference(verifications[1])),
        "4": list(scheduled_l4.difference(verifications[2])),
        "5": list(scheduled_l5.difference(verifications[3])),
    }


def query_verifications_v1(block_id: str, params: Optional[Dict[str, Any]] = None) -> Union[List[Any], Dict[str, List[Any]]]:
    """Query verifications for a block ID on a level, or all levels"""
    _log.info(f"Getting verifications for {block_id}, params {params}")
    level = int(params.get("level") or "0") if params else 0
    blocks = _get_verification_records(block_id, level)
    _log.info(f"Response from verification DAO: {blocks}")
    return blocks


def _get_verification_records(block_id: str, level: int = 0) -> Union[List[Any], Dict[str, List[Any]]]:
    if level:
        if level in [2, 3, 4, 5]:
            return _level_records(block_id, level)
        raise exceptions.InvalidNodeLevel(f"Level {level} not valid.")
    else:
        return _all_records(block_id)


def _level_records(block_id: str, level: int) -> List[Any]:
    return [storage.get_json_from_object(key) for key in storage.list_objects(f"BLOCK/{block_id}-l{level}")]


def _all_records(block_id: str) -> Dict[str, List[Any]]:
    return {"2": _level_records(block_id, 2), "3": _level_records(block_id, 3), "4": _level_records(block_id, 4), "5": _level_records(block_id, 5)}

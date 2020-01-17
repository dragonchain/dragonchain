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
from typing import List, Dict, Set, Any

import fastjsonschema

from dragonchain.lib import keys
from dragonchain.lib.dto import schema
from dragonchain.lib.dto import model

_validate_l2_block_at_rest = fastjsonschema.compile(schema.l2_block_at_rest_schema)


def new_from_at_rest(block: Dict[str, Any]) -> "L2BlockModel":
    """
    Used in querying from the DAO
    Input: Block::L2::AtRest DTO
    Returns: BlockModel object
    """
    # Validate inputted schema
    _validate_l2_block_at_rest(block)
    if block.get("version") == "1":
        return L2BlockModel(
            dc_id=block["header"]["dc_id"],
            current_ddss=block["header"].get("current_ddss"),
            block_id=block["header"]["block_id"],
            timestamp=block["header"].get("timestamp") or "-1",
            prev_proof=block["header"]["prev_proof"],
            scheme=block["proof"]["scheme"],
            proof=block["proof"]["proof"],
            nonce=block["proof"].get("nonce"),
            l1_dc_id=block["validation"]["dc_id"],
            l1_block_id=block["validation"]["block_id"],
            l1_proof=block["validation"]["stripped_proof"],
            validations_str=block["validation"]["transactions"],
        )
    else:
        raise NotImplementedError(f"Version {block.get('version')} is not supported")


def export_broadcast_dto(l2_blocks: List[Dict[str, Any]], l1_block: Dict[str, Any]) -> Dict[str, Any]:
    stripped_proof = l1_block["proof"]["proof"]
    l1_block_id = l1_block["header"]["block_id"]
    return {
        "version": "1",
        "payload": {"header": {"dc_id": keys.get_public_id(), "block_id": l1_block_id, "stripped_proof": stripped_proof}, "l2-blocks": l2_blocks},
    }


class L2BlockModel(model.BlockModel):
    """
    BlockModel class is an abstracted representation of a block object
    """

    def __init__(
        self,
        dc_id=None,
        current_ddss=None,
        block_id=None,
        timestamp=None,
        prev_proof="",
        scheme="",
        proof="",
        nonce=None,
        l1_dc_id=None,
        l1_block_id=None,
        l1_proof=None,
        validations_str=None,
        validations_dict=None,
    ):
        """Model Constructor"""
        self.dc_id = dc_id
        self.current_ddss = current_ddss
        self.block_id = block_id
        if block_id:
            self.prev_id = str(int(block_id) - 1)
        self.timestamp = timestamp
        self.prev_proof = prev_proof
        self.scheme = scheme
        self.proof = proof
        self.nonce = nonce
        self.l1_dc_id = l1_dc_id
        self.l1_block_id = l1_block_id
        self.l1_proof = l1_proof
        self.validations_str = validations_str
        self.validations_dict = validations_dict
        # Validations seperated into dict object and stringified version for deterministic hashing/signing
        if validations_str and not validations_dict:
            self.validations_dict = json.loads(validations_str)
        if validations_dict and not validations_str:
            self.validations_str = json.dumps(validations_dict, separators=(",", ":"))

    def set_validations_dict(self, validations_dict: dict) -> None:
        self.validations_dict = validations_dict
        self.validations_str = json.dumps(validations_dict, separators=(",", ":"))

    def set_validations_str(self, validations_str: str) -> None:
        self.validations_str = validations_str
        self.validations_dict = json.loads(validations_str)

    def get_associated_l1_dcid(self) -> str:
        """Interface function for compatibility"""
        return self.l1_dc_id

    def get_associated_l1_block_id(self) -> Set[str]:
        """Interface function for compatibility"""
        return {self.l1_block_id}

    def export_as_at_rest(self) -> Dict[str, Any]:
        """Export the L2 block that is stored/brodcast/sent for receipt"""
        proof = None
        if self.scheme == "trust":
            proof = {"scheme": self.scheme, "proof": self.proof}
        else:
            proof = {"scheme": self.scheme, "proof": self.proof, "nonce": self.nonce}
        return {
            "version": "1",
            "dcrn": schema.DCRN.Block_L2_At_Rest.value,
            "header": {
                "dc_id": self.dc_id,
                "current_ddss": self.current_ddss,
                "level": 2,
                "block_id": self.block_id,
                "timestamp": self.timestamp,
                "prev_proof": self.prev_proof,
            },
            "validation": {
                "dc_id": self.l1_dc_id,
                "block_id": self.l1_block_id,
                "stripped_proof": self.l1_proof,
                "transactions": self.validations_str,
            },
            "proof": proof,
        }

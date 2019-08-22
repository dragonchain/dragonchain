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

from typing import Dict, List, Set, Any

import fastjsonschema

from dragonchain.lib import keys
from dragonchain.lib.dto import schema
from dragonchain.lib.dto import model

_validate_l3_block_at_rest = fastjsonschema.compile(schema.l3_block_at_rest_schema)


def new_from_at_rest(block: Dict[str, Any]) -> "L3BlockModel":
    """
    Used in querying from the DAO
    Input: Block::L3::AtRest DTO
    Returns: BlockModel object
    """
    # Validate inputted schema
    _validate_l3_block_at_rest(block)

    if block.get("version") == "2" or block.get("version") == "1":
        return L3BlockModel(
            dc_id=block["header"]["dc_id"],
            current_ddss=block["header"].get("current_ddss"),
            block_id=block["header"]["block_id"],
            timestamp=block["header"]["timestamp"],
            prev_proof=block["header"]["prev_proof"],
            scheme=block["proof"]["scheme"],
            proof=block["proof"]["proof"],
            nonce=block["proof"].get("nonce"),
            l1_dc_id=block["l2-validations"]["l1_dc_id"],
            l1_block_id=block["l2-validations"]["l1_block_id"],
            l1_proof=block["l2-validations"]["l1_proof"],
            l2_proofs=block["l2-validations"].get("l2_proofs") or None,
            l2_count=block["l2-validations"]["count"],
            ddss=block["l2-validations"]["ddss"],
            regions=block["l2-validations"]["regions"],
            clouds=block["l2-validations"]["clouds"],
        )
    else:
        raise NotImplementedError(f"Version {block.get('version')} is not supported")


def export_broadcast_dto(l3_blocks: List[Dict[str, Any]], l1_block: Dict[str, Any]) -> Dict[str, Any]:
    stripped_proof = l1_block["proof"]["proof"]
    l1_block_id = l1_block["header"]["block_id"]
    return {
        "version": "1",
        "payload": {"header": {"dc_id": keys.get_public_id(), "block_id": l1_block_id, "stripped_proof": stripped_proof}, "l3-blocks": l3_blocks},
    }


class L3BlockModel(model.BlockModel):
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
        l2_proofs=None,
        l2_count=None,
        ddss=None,
        regions=None,
        clouds=None,
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
        self.l2_proofs = l2_proofs
        self.ddss = ddss
        self.l2_count = l2_count
        self.regions = regions
        self.clouds = clouds

    def get_associated_l1_dcid(self) -> str:
        """Interface function for compatibility"""
        return self.l1_dc_id

    def get_associated_l1_block_id(self) -> Set[str]:
        """Interface function for compatibility"""
        return {self.l1_block_id}

    def export_as_at_rest(self) -> Dict[str, Any]:
        """Export the L3 block that is stored/brodcast/sent for receipt"""
        proof = None
        if self.scheme == "trust":
            proof = {"scheme": self.scheme, "proof": self.proof}
        else:
            proof = {"scheme": self.scheme, "proof": self.proof, "nonce": self.nonce}
        if self.l2_proofs is not None:
            return {
                "version": "2",
                "dcrn": schema.DCRN.Block_L3_At_Rest.value,
                "header": {
                    "dc_id": self.dc_id,
                    "current_ddss": self.current_ddss,
                    "level": 3,
                    "block_id": self.block_id,
                    "timestamp": self.timestamp,
                    "prev_proof": self.prev_proof,
                },
                "l2-validations": {
                    "l1_dc_id": self.l1_dc_id,
                    "l1_block_id": self.l1_block_id,
                    "l1_proof": self.l1_proof,
                    "l2_proofs": self.l2_proofs,
                    "ddss": self.ddss,
                    "count": self.l2_count,
                    "regions": self.regions,
                    "clouds": self.clouds,
                },
                "proof": proof,
            }
        else:
            return {
                "version": "1",
                "dcrn": schema.DCRN.Block_L3_At_Rest.value,
                "header": {
                    "dc_id": self.dc_id,
                    "current_ddss": self.current_ddss,
                    "level": 3,
                    "block_id": self.block_id,
                    "timestamp": self.timestamp,
                    "prev_proof": self.prev_proof,
                },
                "l2-validations": {
                    "l1_dc_id": self.l1_dc_id,
                    "l1_block_id": self.l1_block_id,
                    "l1_proof": self.l1_proof,
                    "ddss": self.ddss,
                    "count": self.l2_count,
                    "regions": self.regions,
                    "clouds": self.clouds,
                },
                "proof": proof,
            }

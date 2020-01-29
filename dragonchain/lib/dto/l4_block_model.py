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

from typing import List, Dict, Set, Any

import fastjsonschema

from dragonchain.lib.dto import schema
from dragonchain.lib.dto import model

_validate_l4_block_at_rest = fastjsonschema.compile(schema.l4_block_at_rest_schema)


def new_from_at_rest(block: Dict[str, Any]) -> "L4BlockModel":
    """
    Used in querying from the DAO
    Input: Block::L4::AtRest DTO
    Returns: BlockModel object
    """
    # Validate inputted schema
    _validate_l4_block_at_rest(block)
    validations = []
    for item in block["l3-validations"]:
        validations.append({"l3_dc_id": item["l3_dc_id"], "l3_block_id": item["l3_block_id"], "l3_proof": item["l3_proof"], "valid": item["valid"]})
    if block.get("version") == "3":
        return L4BlockModel(
            dc_id=block["header"]["dc_id"],
            current_ddss=block["header"].get("current_ddss"),
            block_id=block["header"]["block_id"],
            timestamp=block["header"].get("timestamp") or "-1",
            prev_proof=block["header"]["prev_proof"],
            scheme=block["proof"]["scheme"],
            proof=block["proof"]["proof"],
            nonce=block["proof"].get("nonce"),
            l1_dc_id=block["header"]["l1_dc_id"],
            l1_block_id=block["header"]["l1_block_id"],
            l1_proof=block["header"]["l1_proof"],
            validations=validations,
            chain_name=block["header"]["chain_name"],
        )
    elif block.get("version") == "2":
        return L4BlockModel(
            dc_id=block["header"]["dc_id"],
            current_ddss=block["header"].get("current_ddss"),
            block_id=block["header"]["block_id"],
            timestamp=block["header"].get("timestamp") or "-1",
            prev_proof=block["header"]["prev_proof"],
            scheme=block["proof"]["scheme"],
            proof=block["proof"]["proof"],
            nonce=block["proof"].get("nonce"),
            l1_dc_id=block["header"]["l1_dc_id"],
            l1_block_id=block["header"]["l1_block_id"],
            l1_proof=block["header"]["l1_proof"],
            validations=validations,
        )
    else:
        raise NotImplementedError(f"Version {block.get('version')} is not supported")


def export_broadcast_dto(l4_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"version": "1", "payload": {"l4-blocks": l4_blocks}}


class L4BlockModel(model.BlockModel):
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
        validations=None,
        chain_name="",
    ):
        """Model Constructor"""
        if validations is None:
            validations = []
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
        self.validations = validations
        self.chain_name = chain_name

    def get_associated_l1_dcid(self) -> str:
        """Interface function for compatibility"""
        return self.l1_dc_id

    def get_associated_l1_block_id(self) -> Set[str]:
        """Interface function for compatibility"""
        return {self.l1_block_id}

    def export_as_at_rest(self) -> Dict[str, Any]:
        """Export the L4 block that is stored/brodcast/sent for receipt"""
        proof = None
        if self.scheme == "trust":
            proof = {"scheme": self.scheme, "proof": self.proof}
        else:
            proof = {"scheme": self.scheme, "proof": self.proof, "nonce": self.nonce}
        return {
            "version": "3",
            "dcrn": schema.DCRN.Block_L4_At_Rest.value,
            "header": {
                "chain_name": self.chain_name,
                "dc_id": self.dc_id,
                "current_ddss": self.current_ddss,
                "level": 4,
                "block_id": self.block_id,
                "timestamp": self.timestamp,
                "l1_dc_id": self.l1_dc_id,
                "l1_block_id": self.l1_block_id,
                "l1_proof": self.l1_proof,
                "prev_proof": self.prev_proof,
            },
            "l3-validations": self.validations,
            "proof": proof,
        }

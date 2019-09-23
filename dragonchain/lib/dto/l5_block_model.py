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

import json

import fastjsonschema

from dragonchain.lib import keys
from dragonchain.lib.dto import schema
from dragonchain.lib.dto import model

_validate_l5_block_at_rest = fastjsonschema.compile(schema.l5_block_at_rest_schema)


def new_from_at_rest(block: dict) -> "L5BlockModel":
    """
    Used in querying from the DAO
    Input: Block::L4::AtRest DTO
    Returns: BlockModel object
    """
    # Validate inputted schema
    _validate_l5_block_at_rest(block)
    if block.get("version") == "1":
        return L5BlockModel(
            dc_id=block["header"]["dc_id"],
            current_ddss=block["header"].get("current_ddss"),
            block_id=block["header"]["block_id"],
            timestamp=block["header"].get("timestamp") or "-1",
            prev_proof=block["header"]["prev_proof"],
            scheme=block["proof"]["scheme"],
            proof=block["proof"]["proof"],
            transaction_hash=block["proof"]["transaction_hash"],
            network=block["proof"]["network"],
            block_last_sent_at=block["proof"]["block_last_sent_at"],
            nonce=block["proof"].get("nonce"),
            l4_blocks=block["l4-blocks"],
        )
    else:
        raise NotImplementedError(f"Version {block.get('version')} is not supported")


class L5BlockModel(model.BlockModel):
    """
    BlockModel class is an abstracted representation of a block object
    """

    #  Take in all possible data points for a given type of block, and validate
    def __init__(
        self,
        dc_id=None,
        current_ddss=None,
        block_id=None,
        timestamp=None,
        prev_proof="",
        scheme="",
        proof="",
        transaction_hash=None,
        network=None,
        nonce=None,
        l4_blocks=None,
        block_last_sent_at=None,
    ):
        """Model Constructor"""
        if l4_blocks is None:
            l4_blocks = []
        if transaction_hash is None:
            transaction_hash = []
        self.dc_id = dc_id
        self.current_ddss = current_ddss
        self.block_id = block_id
        if block_id:
            self.prev_id = str(int(block_id) - 1)
        self.timestamp = timestamp
        self.prev_proof = prev_proof
        self.transaction_hash = transaction_hash
        self.scheme = scheme
        self.proof = proof
        self.nonce = nonce
        self.network = network
        self.l4_blocks = l4_blocks
        self.block_last_sent_at = block_last_sent_at

    def get_associated_l1_block_id(self) -> set:
        """Interface function for compatibility"""
        # Scrape the L4 blocks array to find all entries in the L5 block for this L1
        l4_blocks_for_l1 = set()
        for x in self.l4_blocks:
            l4_block_candidate = json.loads(x)
            if l4_block_candidate["l1_dc_id"] == keys.get_public_id():
                l4_blocks_for_l1.add(l4_block_candidate["l1_block_id"])
            # else no-op
        return l4_blocks_for_l1

    def export_as_at_rest(self) -> dict:
        """Export the L5 block that is stored/brodcast/sent for receipt"""
        proof = None
        if self.scheme == "trust":
            proof = {
                "scheme": self.scheme,
                "transaction_hash": self.transaction_hash,
                "block_last_sent_at": self.block_last_sent_at,
                "network": self.network,
                "proof": self.proof,
            }
        else:
            proof = {
                "scheme": self.scheme,
                "proof": self.proof,
                "transaction_hash": self.transaction_hash,
                "block_last_sent_at": self.block_last_sent_at,
                "network": self.network,
                "nonce": self.nonce,
            }
        return {
            "version": "1",
            "dcrn": schema.DCRN.Block_L5_At_Rest.value,
            "header": {
                "dc_id": self.dc_id,
                "current_ddss": self.current_ddss,
                "level": 5,
                "block_id": self.block_id,
                "timestamp": self.timestamp,
                "prev_proof": self.prev_proof,
            },
            "l4-blocks": self.l4_blocks,
            "proof": proof,
        }

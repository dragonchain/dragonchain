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
from typing import cast, Dict, Any, TYPE_CHECKING

from dragonchain.broadcast_processor import broadcast_functions
from dragonchain.lib.interfaces import storage
from dragonchain.lib.dto import l2_block_model
from dragonchain.lib.dto import l3_block_model
from dragonchain.lib.dto import l4_block_model
from dragonchain.lib.dto import l5_block_model
from dragonchain.lib import matchmaking
from dragonchain.lib import keys
from dragonchain.lib import queue
from dragonchain.lib import authorization
from dragonchain import exceptions
from dragonchain import logger


if TYPE_CHECKING:
    from dragonchain.lib.dto import model  # noqa: F401

REDIS_HOST = os.environ["REDIS_ENDPOINT"]
REDIS_PORT = os.environ["REDIS_PORT"]
INTERNAL_ID = os.environ["INTERNAL_ID"]
FOLDER = "BLOCK"

_log = logger.get_logger()


def process_receipt_v1(block_dto: Dict[str, Any]) -> None:
    if not block_dto:
        raise exceptions.ValidationException("block_dto missing")
    _log.info(f"[RECEIPT] Got receipt from L{block_dto['header']['level']}: {block_dto}")
    block_model = cast("model.BlockModel", None)  # This will always get defined, or it will raise
    level_received_from = block_dto["header"]["level"]
    if level_received_from == 2:
        block_model = l2_block_model.new_from_at_rest(block_dto)
    elif level_received_from == 3:
        block_model = l3_block_model.new_from_at_rest(block_dto)
    elif level_received_from == 4:
        block_model = l4_block_model.new_from_at_rest(block_dto)
    elif level_received_from == 5:
        block_model = l5_block_model.new_from_at_rest(block_dto)
    else:
        raise exceptions.InvalidNodeLevel("Unsupported level receipt")

    _log.info(f"Block model {block_model.__dict__}")
    l1_block_id_set = block_model.get_associated_l1_block_id()

    _log.info(f"Processing receipt for blocks {l1_block_id_set} from L{level_received_from}")
    for l1_block_id in l1_block_id_set:
        # Check that the chain which sent this receipt is in our claims, and that this L1 block is accepting receipts for this level
        validations = matchmaking.get_claim_check(l1_block_id)["validations"][f"l{level_received_from}"]
        if (block_model.dc_id in validations) and broadcast_functions.is_block_accepting_verifications_from_level(l1_block_id, level_received_from):
            _log.info(f"Verified that block {l1_block_id} was sent. Inserting receipt")
            storage.put_object_as_json(f"{FOLDER}/{l1_block_id}-l{level_received_from}-{block_model.dc_id}", block_model.export_as_at_rest())
            # Set new receipt for matchmaking claim check
            try:
                block_id = block_model.block_id
                proof = block_model.proof
                dc_id = block_model.dc_id
                matchmaking.add_receipt(l1_block_id, level_received_from, dc_id, block_id, proof)
            except Exception:
                _log.exception("matchmaking add_receipt failed!")
            # Update the broadcast system about this receipt
            broadcast_functions.set_receieved_verification_for_block_from_chain_sync(l1_block_id, level_received_from, block_model.dc_id)
        else:
            _log.warning(
                f"Chain {block_model.dc_id} (level {level_received_from}) returned a receipt that wasn't expected (possibly expired?) for block {l1_block_id}. Rejecting receipt"  # noqa: B950
            )
            raise exceptions.NotAcceptingVerifications(f"Not accepting verifications for block {l1_block_id} from {block_model.dc_id}")


def enqueue_item_for_verification_v1(content: Dict[str, str], deadline: int) -> None:
    queue.enqueue_item(content, deadline)


def get_local_claim_v1(block_id: str) -> dict:
    return matchmaking.get_claim_check(block_id)


def register_interchain_auth_v1(chain_registration_body: Dict[str, str]) -> None:
    dcid = chain_registration_body["dcid"]
    key = chain_registration_body["key"]
    signature = chain_registration_body["signature"]

    # Initialize keys with chain id as public key (dont need to pull from matchmaking)
    requester_keys = keys.DCKeys(pull_keys=False).initialize(public_key_string=dcid, hash_type="sha256")

    if not requester_keys.check_signature(f"{keys.get_public_id()}_{key}".encode("utf-8"), signature):
        _log.info(f"invalid signature for interchain key registration from {dcid}")
        raise exceptions.UnauthorizedException("Invalid signature authorization")

    # Authorization successful, now register actual key
    if not authorization.save_interchain_auth_key(dcid, key):
        # If registering interchain auth key wasn't successful, something has gone wrong
        raise RuntimeError("Authorization registration failure")

    _log.info(f"successfully registered interchain auth key with {dcid}")

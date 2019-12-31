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

import os
import json
from typing import TYPE_CHECKING, cast

import requests

from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib import authorization
from dragonchain.lib import matchmaking
from dragonchain.lib.database import redis

if TYPE_CHECKING:
    from dragonchain.lib.dto import l5_block_model
    from dragonchain.lib.dto import model

LEVEL = os.environ["LEVEL"]

_log = logger.get_logger()


def dispatch(block: "model.BlockModel") -> None:
    if LEVEL == "5":
        _log.info(f"[BROADCAST] Sending receipts for block {block.block_id} down to lower nodes")
        send_receipts(cast("l5_block_model.L5BlockModel", block))  # This should always be an l5 block when l5
    else:
        _log.info(f"[BROADCAST] Sending receipt for block down to lower node: {block.get_associated_l1_dcid()}")
        send_receipt(block)


def send_receipt(block: "model.BlockModel") -> None:
    try:
        dcid = block.get_associated_l1_dcid()
        full_path = "/v1/receipt"
        url = f"{matchmaking.get_dragonchain_address(dcid)}{full_path}"
        headers, data = authorization.generate_authenticated_request("POST", dcid, full_path, block.export_as_at_rest())
        _log.info(f"----> {url}")
        r = requests.post(url, data=data, headers=headers, timeout=30)
        _log.info(f"<---- {r.status_code} {r.text}")
        if r.status_code != 200:
            _log.info(f"[BROADCAST] WARNING: failed to transmit to {dcid} with error {r.text}")
        else:
            _log.info("[BROADCAST] Sucessful receipt sent down to L1")
    except Exception:
        _log.error(f"[BROADCAST] ERROR: Couldn't broadcast receipt down to {dcid}! Ignoring")


def send_receipts(l5_block: "l5_block_model.L5BlockModel") -> None:
    receipt_path = "/v1/receipt"
    get_claim_path = "/v1/claim"
    chain_id_set = set()
    _log.info(f"l5 block to loop {l5_block.__dict__}")
    _log.info(f"Sending receipts to {len(l5_block.l4_blocks)} lower nodes")
    for l4_block in l5_block.l4_blocks:
        try:
            block_dictionary = json.loads(l4_block)
            chain_id = block_dictionary["l1_dc_id"]
            block = block_dictionary["l1_block_id"]
            full_claim_path = f"{get_claim_path}/{block}"
            # Get the claim data for billing
            claim_url = f"{matchmaking.get_dragonchain_address(chain_id)}{full_claim_path}"
            headers, _ = authorization.generate_authenticated_request("GET", chain_id, full_claim_path)
            _log.info(f"getting claim for {block} from {chain_id}")
            try:
                _log.info(f"----> {claim_url}")
                r = requests.get(claim_url, headers=headers, timeout=30)
                _log.info(f"<---- {r.status_code} {r.text}")
            except Exception:
                _log.exception("Failed to get claim!")
            if r.status_code != 200:
                _log.error(f"Claim check failed! Rejecting block {block} from {chain_id}")
                continue
            else:
                claim = r.json()
                # Add this L5's proof to the block
                _log.info(f"Claim received from l1 {claim}")
                _log.info(f"data points blockid {l5_block.block_id}  signature {l5_block.proof}")
                block_data = {}
                block_data["blockId"] = l5_block.block_id
                block_data["signature"] = l5_block.proof
                claim["validations"]["l5"][l5_block.dc_id] = block_data
                chain_id_set.add(chain_id)
                _log.info(f"Sending filled claim {claim}")
                try:
                    claim_check_id = f"{chain_id}-{block}"
                    matchmaking.resolve_claim_check(claim_check_id)
                except exceptions.MatchmakingRetryableError:  # any 500-level server errors
                    _log.exception(f"Adding claim to failed queue.  Claim ID: {claim_check_id}")
                    redis.sadd_sync("mq:failed-claims", claim_check_id)  # using a set avoids duplicates
                except Exception:
                    _log.exception("Failure to finalize claim in matchmaking. Sending receipts to lower level nodes.")
        except Exception as e:
            _log.exception(f"[BROADCAST] Error while trying to broadcast down for l4 block {l4_block}\n{e}\n!Will ignore this broadcast!")

    payload = l5_block.export_as_at_rest()
    for chain_id in chain_id_set:
        try:
            headers, data = authorization.generate_authenticated_request("POST", chain_id, receipt_path, payload)
            url = f"{matchmaking.get_dragonchain_address(chain_id)}{receipt_path}"
            _log.info(f"----> {url}")
            r = requests.post(url, data=data, headers=headers, timeout=30)
            _log.info(f"<---- {r.status_code} {r.text}")
            if r.status_code != 200:
                # TODO failed to enqueue block to specific l1, consider another call to matchmaking, etc
                _log.info(f"[BROADCAST] WARNING: failed to transmit to {chain_id} with error {r.text}")
            else:
                _log.info("[BROADCAST] Sucessful receipt sent down to L1")
        except Exception:
            _log.error(f"[BROADCAST] ERROR: Couldn't broadcast receipt down to {chain_id}! Ignoring")

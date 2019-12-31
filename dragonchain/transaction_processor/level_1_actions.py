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
import time
from typing import List, TYPE_CHECKING

from dragonchain.broadcast_processor import broadcast_functions
from dragonchain.lib.dao import transaction_dao
from dragonchain.lib.dao import transaction_type_dao
from dragonchain.lib.dao import block_dao
from dragonchain.lib.dto import l1_block_model
from dragonchain.lib import keys
from dragonchain.lib import matchmaking
from dragonchain.lib import queue
from dragonchain.lib import callback
from dragonchain import logger
from dragonchain import exceptions

if TYPE_CHECKING:
    from dragonchain.lib.dto import transaction_model


PROOF_SCHEME = os.environ["PROOF_SCHEME"].lower()
BROADCAST = os.environ["BROADCAST"].lower() != "false"

_log = logger.get_logger()


def execute() -> None:
    """Pops transactions off the queue, fixates them into a block and adds it to the chain"""
    if BROADCAST:
        try:
            matchmaking.renew_registration_if_necessary()
        except (exceptions.MatchmakingError, exceptions.MatchmakingRetryableError):
            _log.warning("Could not register with matchmaking! Is your Dragon Net configuration valid?")
    t0 = time.time()

    # Pop off of queue
    new_signable_txns = get_new_transactions()
    t1 = time.time()

    # Get current block id
    current_block_id = l1_block_model.get_current_block_id()
    # Activate any new custom indexes if necessary
    activate_pending_indexes_if_necessary(current_block_id)
    t2 = time.time()

    if len(new_signable_txns) > 0:
        # Sign / validate transactions
        signed_transactions = process_transactions(new_signable_txns)
        t3 = time.time()

        # Create the block
        block = create_block(signed_transactions, current_block_id)
        t4 = time.time()

        # Store the block
        store_data(block)
        t5 = time.time()

        # Clear our processing queue (finished successfully)
        clear_processing_transactions()

        total = t5 - t0
        _log.info(f"[L1] Processed {len(signed_transactions)} transactions in {total:.4f} seconds")
        _log.info(f"[L1] Retrieving Txns From queue: {t1 - t0:.4f} sec ({((t1 - t0) / total) * 100:.1f}% of processing)")
        _log.info(f"[L1] Activating pending transaction types: {t2 - t1:.4f} sec ({((t2 - t1) / total) * 100:.1f}% of processing)")
        _log.info(f"[L1] Signing/Fixating Txns: {t3 - t2:.4f} sec ({((t3 - t2) / total) * 100:.1f}% of processing)")
        _log.info(f"[L1] Creating block model: {t4 - t3:.4f} sec ({((t4 - t3) / total) * 100:.1f}% of processing)")
        _log.info(f"[L1] Uploading data: {t5 - t4:.4f} sec ({((t5 - t4) / total) * 100:.1f}% of processing)")


def activate_pending_indexes_if_necessary(block_id: str) -> None:
    """This function is used to activate a new custom index at a precise time so that indexes can be regenerated in the future if necessary
    Args:
        block_id: The block id to activate the transaction types (should be the next block)
    """
    transaction_type_dao.activate_transaction_types_if_necessary(block_id)


def clear_processing_transactions() -> None:
    queue.clear_processing_queue()


def get_new_transactions() -> List["transaction_model.TransactionModel"]:
    # Safety check to recover after unexpected crash while creating last block if necessary
    queue.check_and_recover_processing_if_necessary()
    return queue.get_new_transactions()


def process_transactions(raw_transactions: List["transaction_model.TransactionModel"]) -> List["transaction_model.TransactionModel"]:
    signed_transactions = []
    block_id = l1_block_model.get_current_block_id()
    _log.info(f"[L1] Starting processing for block {block_id}.")

    for transaction in raw_transactions:
        sign_transaction(transaction, block_id)
        signed_transactions.append(transaction)
        if transaction.invoker is not None:
            #  Contract invocation callbacks
            callback.fire_if_exists(transaction.invoker, transaction)
        else:
            #  Pure ledgering transaction callbacks
            callback.fire_if_exists(transaction.txn_id, transaction)

    _log.info("[L1] Signing complete")

    return signed_transactions


def sign_transaction(transaction: "transaction_model.TransactionModel", block_id: str) -> None:
    """Sign a transaction model for a given block
    Args:
        transaction: TransactionModel to be signed
        block_id: block id to give to this transaction before Signing
    """
    transaction.block_id = block_id
    full_hash, signature = keys.get_my_keys().sign_transaction(transaction)
    transaction.full_hash = full_hash
    transaction.signature = signature


def create_block(signed_transactions: List["transaction_model.TransactionModel"], block_id: str) -> l1_block_model.L1BlockModel:
    # Get prior block hash and ID, and create new block with the fixated transactions
    previous_proof = block_dao.get_last_block_proof()
    block = l1_block_model.new_from_full_transactions(
        signed_transactions, block_id, previous_proof.get("block_id") or "", previous_proof.get("proof") or ""
    )
    _log.info(f"[L1] Next block created. Previous block hash: {previous_proof.get('proof')}, previous block ID: {previous_proof.get('block_id')}")

    _log.info("[L1] Signing block")
    sign_block(block)

    return block


def sign_block(block: l1_block_model.L1BlockModel) -> None:
    # Strip payloads
    _log.info("[L1] Stripping payloads and signing")
    block.strip_payloads()

    # Add proof, currently work or trust
    if PROOF_SCHEME == "work":
        _log.info("[L1] Doing PoW...")
        block.proof, block.nonce = keys.get_my_keys().pow_block(block)
        block.scheme = "work"
    else:
        _log.info("[L1] Signing block...")
        block.proof = keys.get_my_keys().sign_block(block)
        block.scheme = "trust"


def store_data(block: l1_block_model.L1BlockModel) -> None:
    _log.info("[L1] Extracting custom indexes from transactions")
    txn_type_models = transaction_type_dao.get_registered_transaction_types_or_default(block.get_txn_types())
    block.set_custom_indexes(txn_type_models)
    _log.info("[L1] Uploading full transactions")
    transaction_dao.store_full_txns(block)
    _log.info("[L1] Uploading stripped block")
    block_dao.insert_block(block)
    _log.info("[L1] Removing transaction stubs")
    queue.remove_transaction_stubs(block.transactions)
    _log.info("[L1] Adding record in block broadcast service")
    if not BROADCAST:
        return
    broadcast_functions.set_current_block_level_sync(block.block_id, 2)
    broadcast_functions.schedule_block_for_broadcast_sync(block.block_id)

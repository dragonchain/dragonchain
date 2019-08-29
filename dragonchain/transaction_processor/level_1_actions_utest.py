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

import unittest
from unittest.mock import patch, MagicMock, ANY, call

from dragonchain import test_env  # noqa: F401
from dragonchain.transaction_processor import level_1_actions


class TestLevelOneActions(unittest.TestCase):
    @patch("dragonchain.lib.dto.l1_block_model.get_current_block_id", return_value="12345")
    @patch("dragonchain.transaction_processor.level_1_actions.activate_pending_indexes_if_necessary")
    @patch("dragonchain.transaction_processor.level_1_actions.matchmaking")
    @patch("dragonchain.transaction_processor.level_1_actions.process_transactions", return_value="Signed Transactions")
    @patch("dragonchain.transaction_processor.level_1_actions.create_block", return_value=MagicMock(block_id="12345"))
    @patch("dragonchain.transaction_processor.level_1_actions.store_data")
    @patch("dragonchain.transaction_processor.level_1_actions.get_new_transactions", return_value=[{"new": "txn"}])
    @patch("dragonchain.transaction_processor.level_1_actions.clear_processing_transactions")
    def test_execute_calls_correct_functions(
        self,
        mock_clear_processing,
        mock_get_transactions,
        mock_store_data,
        mock_create_block,
        mock_process_transactions,
        mock_matchmaking,
        mock_activate_indexes,
        mock_get_block_id,
    ):
        level_1_actions.execute()

        mock_activate_indexes.assert_called_once()
        mock_get_transactions.assert_called_once()
        mock_process_transactions.assert_called_once_with([{"new": "txn"}])
        mock_create_block.assert_called_once_with("Signed Transactions", "12345")
        mock_store_data.assert_called_once()
        mock_clear_processing.assert_called_once()

    @patch("dragonchain.transaction_processor.level_1_actions.activate_pending_indexes_if_necessary")
    @patch("dragonchain.transaction_processor.level_1_actions.matchmaking")
    @patch("dragonchain.transaction_processor.level_1_actions.process_transactions")
    @patch("dragonchain.transaction_processor.level_1_actions.create_block")
    @patch("dragonchain.transaction_processor.level_1_actions.store_data")
    @patch("dragonchain.transaction_processor.level_1_actions.get_new_transactions", return_value=[])
    @patch("dragonchain.transaction_processor.level_1_actions.clear_processing_transactions")
    def test_execute_no_ops_on_empty_queue(
        self,
        mock_clear_processing,
        mock_get_transactions,
        mock_store_data,
        mock_create_block,
        mock_process_transactions,
        mock_matchmaking,
        mock_activate_indexes,
    ):
        level_1_actions.execute()

        mock_activate_indexes.assert_called_once()
        mock_get_transactions.assert_called_once()
        mock_process_transactions.assert_not_called()
        mock_create_block.assert_not_called()
        mock_store_data.assert_not_called()
        mock_clear_processing.assert_not_called()

    @patch("dragonchain.transaction_processor.level_1_actions.queue.check_and_recover_processing_if_necessary")
    @patch("dragonchain.transaction_processor.level_1_actions.queue.get_new_transactions")
    def test_get_new_transactions_calls_incoming_queue(self, mock_get_txns, mock_recover):
        level_1_actions.get_new_transactions()
        mock_get_txns.assert_called_once()

    @patch("dragonchain.transaction_processor.level_1_actions.queue.check_and_recover_processing_if_necessary")
    @patch("dragonchain.transaction_processor.level_1_actions.queue.get_new_transactions")
    def test_get_new_transactions_checks_for_recovery(self, mock_get_txns, mock_recover):
        level_1_actions.get_new_transactions()
        mock_recover.assert_called_once()

    @patch("dragonchain.transaction_processor.level_1_actions.callback")
    @patch("dragonchain.transaction_processor.level_1_actions.sign_transaction")
    def test_process_transactions_signs_all_transactions(self, mock_sign, mock_callback):
        txn_model_1 = MagicMock()
        txn_model_2 = MagicMock()
        response = level_1_actions.process_transactions([txn_model_1, txn_model_2])
        self.assertEqual(response, [txn_model_1, txn_model_2])  # should be the same because sign is mocked
        mock_sign.assert_has_calls([call(txn_model_1, ANY), call(txn_model_2, ANY)])

    @patch("dragonchain.transaction_processor.level_1_actions.callback.fire_if_exists")
    @patch("dragonchain.transaction_processor.level_1_actions.sign_transaction")
    def test_process_transactions_finds_contract_id(self, mock_sign, mock_fire_callback):
        fake_txn_model = MagicMock()
        fake_txn_model.invoker = "apple"
        level_1_actions.process_transactions([fake_txn_model])
        mock_fire_callback.assert_called_once_with(fake_txn_model.invoker, fake_txn_model)

    @patch("dragonchain.transaction_processor.level_1_actions.callback.fire_if_exists")
    @patch("dragonchain.transaction_processor.level_1_actions.sign_transaction")
    def test_process_transactions_no_invoker(self, mock_sign, mock_fire_callback):
        fake_txn_model = MagicMock()
        fake_txn_model.txn_id = "test"
        fake_txn_model.invoker = None
        level_1_actions.process_transactions([fake_txn_model])
        mock_fire_callback.assert_called_once_with(fake_txn_model.txn_id, fake_txn_model)

    @patch("dragonchain.transaction_processor.level_1_actions.keys.get_my_keys")
    def test_sign_calls_keys_sign(self, mock_keys):
        mock_keys.return_value = MagicMock(sign_transaction=MagicMock(return_value=("Full Hash", "Signature")))
        mock_transaction_model = MagicMock()
        level_1_actions.sign_transaction(mock_transaction_model, "1234")
        mock_keys.return_value.sign_transaction.assert_called_once_with(mock_transaction_model)
        self.assertEqual(mock_transaction_model.block_id, "1234")
        self.assertEqual(mock_transaction_model.full_hash, "Full Hash")
        self.assertEqual(mock_transaction_model.signature, "Signature")

    @patch("dragonchain.transaction_processor.level_1_actions.block_dao.get_last_block_proof", return_value={"block_id": "1234", "proof": "MyProof"})
    @patch("dragonchain.transaction_processor.level_1_actions.l1_block_model.new_from_full_transactions", return_value="Mock Block")
    @patch("dragonchain.transaction_processor.level_1_actions.sign_block")
    def test_create_block_creates_and_signs(self, mock_sign, mock_new_block, mock_get_proof):
        level_1_actions.create_block([{"Signed": "Txn"}, {"Signed": "Txn2"}], "123")

        mock_get_proof.assert_called_once()
        mock_new_block.assert_called_once_with([{"Signed": "Txn"}, {"Signed": "Txn2"}], "123", "1234", "MyProof")
        mock_sign.assert_called_once_with("Mock Block")

    @patch("dragonchain.transaction_processor.level_1_actions.keys.get_my_keys")
    def test_sign_block_strips_payloads(self, mock_keys):
        mock_block = MagicMock()
        level_1_actions.sign_block(mock_block)
        mock_block.strip_payloads.assert_called_once()

    @patch("dragonchain.transaction_processor.level_1_actions.keys.get_my_keys")
    @patch("dragonchain.transaction_processor.level_1_actions.PROOF_SCHEME", "work")
    def test_sign_block_does_pow(self, mock_keys):
        mock_keys.return_value = MagicMock(pow_block=MagicMock(return_value=("proof", "nonce")))
        mock_block = MagicMock()
        level_1_actions.sign_block(mock_block)

        mock_keys.return_value.pow_block.assert_called_once_with(mock_block)
        self.assertEqual(mock_block.proof, "proof")
        self.assertEqual(mock_block.nonce, "nonce")
        self.assertEqual(mock_block.scheme, "work")

    @patch("dragonchain.transaction_processor.level_1_actions.keys.get_my_keys")
    @patch("dragonchain.transaction_processor.level_1_actions.PROOF_SCHEME", "trust")
    def test_sign_block_does_trust(self, mock_keys):
        mock_keys.return_value = MagicMock(sign_block=MagicMock(return_value="proof"))
        mock_block = MagicMock()
        level_1_actions.sign_block(mock_block)

        mock_keys.return_value.sign_block.assert_called_once_with(mock_block)
        self.assertEqual(mock_block.proof, "proof")
        self.assertEqual(mock_block.scheme, "trust")

    @patch("dragonchain.transaction_processor.level_1_actions.block_dao.insert_block")
    @patch("dragonchain.transaction_processor.level_1_actions.broadcast_functions.set_current_block_level_sync")
    @patch("dragonchain.transaction_processor.level_1_actions.broadcast_functions.schedule_block_for_broadcast_sync")
    @patch("dragonchain.transaction_processor.level_1_actions.transaction_dao.store_full_txns")
    def test_store_data_does_correct_things(self, mock_store, mock_broadcast_schedule_block, mock_broadcast_set_block_level, mock_insert_block):
        mock_block = MagicMock()
        level_1_actions.store_data(mock_block)

        mock_insert_block.assert_called_once_with(mock_block)
        mock_broadcast_set_block_level.assert_called_once_with(mock_block.block_id, 2)
        mock_broadcast_schedule_block.assert_called_once_with(mock_block.block_id)
        mock_store.assert_called_once_with(mock_block)

    @patch("dragonchain.transaction_processor.level_1_actions.activate_pending_indexes_if_necessary")
    def test_activate_pending_indexes_if_necessary(self, mock_activate):
        level_1_actions.activate_pending_indexes_if_necessary("banana4")
        mock_activate.assert_called_once_with("banana4")

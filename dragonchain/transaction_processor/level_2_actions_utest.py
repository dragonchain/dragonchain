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

import unittest
from unittest.mock import patch, MagicMock

from dragonchain import test_env  # noqa: F401
from dragonchain.transaction_processor import level_2_actions


class TestLevelTwoActions(unittest.TestCase):
    @patch("dragonchain.transaction_processor.level_2_actions.matchmaking")
    @patch("dragonchain.transaction_processor.level_2_actions.send_data")
    @patch("dragonchain.transaction_processor.level_2_actions.recurse_if_necessary")
    @patch("dragonchain.transaction_processor.level_2_actions.create_block")
    @patch("dragonchain.transaction_processor.level_2_actions.process_transactions", return_value=True)
    @patch("dragonchain.transaction_processor.level_2_actions.get_new_block")
    @patch("dragonchain.transaction_processor.level_2_actions.verify_transaction_count")
    @patch("dragonchain.transaction_processor.level_2_actions.clear_processing_block")
    def test_execute_calls_correct_functions(
        self, mock_clear_processing, mock_get_block, mock_process, mock_create_block, mock_recurse, mock_send_data, mock_count, mock_matchmaking
    ):
        level_2_actions.execute()

        mock_get_block.assert_called_once()
        mock_process.assert_called_once()
        mock_create_block.assert_called_once()
        mock_send_data.assert_called_once()
        mock_recurse.assert_called_once()
        mock_count.assert_called_once()
        mock_clear_processing.assert_called_once()

    @patch("dragonchain.transaction_processor.level_2_actions.matchmaking")
    @patch("dragonchain.transaction_processor.level_2_actions.send_data")
    @patch("dragonchain.transaction_processor.level_2_actions.recurse_if_necessary")
    @patch("dragonchain.transaction_processor.level_2_actions.create_block")
    @patch("dragonchain.transaction_processor.level_2_actions.verify_transactions")
    @patch("dragonchain.transaction_processor.level_2_actions.verify_block")
    @patch("dragonchain.transaction_processor.level_2_actions.get_verifying_keys")
    @patch("dragonchain.transaction_processor.level_2_actions.get_new_block", return_value=[])
    @patch("dragonchain.transaction_processor.level_2_actions.clear_processing_block")
    def test_execute_no_ops_on_empty_queue(
        self,
        mock_clear_processing,
        mock_get_block,
        mock_get_keys,
        mock_verify_block,
        mock_verify_txn,
        mock_create_block,
        mock_recurse,
        mock_send_data,
        mock_matchmaking,
    ):
        level_2_actions.execute()

        mock_get_block.assert_called_once()
        mock_get_keys.assert_not_called()
        mock_verify_block.assert_not_called()
        mock_verify_txn.assert_not_called()
        mock_create_block.assert_not_called()
        mock_recurse.assert_not_called()
        mock_send_data.assert_not_called()
        mock_clear_processing.assert_not_called()

    @patch("dragonchain.transaction_processor.level_2_actions.queue.check_and_recover_processing_if_necessary")
    @patch("dragonchain.transaction_processor.level_2_actions.queue.get_next_l1_block")
    def test_get_new_block_calls_incoming_queue(self, mock_get_next_block, mock_recover):
        level_2_actions.get_new_block()
        mock_get_next_block.assert_called_once()

    @patch("dragonchain.transaction_processor.level_2_actions.queue.check_and_recover_processing_if_necessary")
    @patch("dragonchain.transaction_processor.level_2_actions.queue.get_next_l1_block")
    def test_get_new_block_checks_for_recovery(self, mock_get_next_block, mock_recover):
        level_2_actions.get_new_block()
        mock_recover.assert_called_once()

    @patch("dragonchain.transaction_processor.level_2_actions.keys.DCKeys", return_value="ChainKeys")
    def test_get_verifying_keys_returns_correct_keys(self, mock_keys):
        self.assertEqual(level_2_actions.get_verifying_keys("MyID"), "ChainKeys")
        mock_keys.assert_called_once_with("MyID")

    def test_keys_verifys_block(self):
        mock_keys = MagicMock()
        mock_block = MagicMock()

        level_2_actions.verify_block(mock_block, mock_keys)
        mock_keys.verify_block.assert_called_once_with(mock_block)

    def test_verify_transactions_verifies_each(self):
        txn_map = {}
        mock_transaction_1 = '{"header":{"txn_id":"1","dc_id":"1","block_id":"1","timestamp":"1234","txn_type":"test","tag":"","invoker":""},"proof":{"full":"","stripped":""},"version":"2"}'  # noqa: B950
        mock_transaction_2 = '{"header":{"txn_id":"2","dc_id":"1","block_id":"1","timestamp":"1234","txn_type":"test","tag":"","invoker":""},"proof":{"full":"","stripped":""},"version":"2"}'  # noqa: B950
        mock_keys = MagicMock()
        mock_keys.verify_stripped_transaction = MagicMock(return_value=True)
        mock_block = MagicMock()
        mock_block.stripped_transactions = [mock_transaction_1, mock_transaction_2]

        level_2_actions.verify_transactions(mock_block, mock_keys, txn_map)
        self.assertTrue(txn_map["1"])
        self.assertTrue(txn_map["2"])

    def test_verify_transactions_skips_invalid(self):
        txn_map = {}
        mock_transaction_1 = '{"header":{"txn_id":"1","dc_id":"1","block_id":"1","timestamp":"1234","txn_type":"test","tag":"","invoker":""},"proof":{"full":"","stripped":""},"version":"2"}'  # noqa: B950
        mock_transaction_2 = "invalid"
        mock_keys = MagicMock()
        mock_keys.verify_stripped_transaction = MagicMock(return_value=True)
        mock_block = MagicMock()
        mock_block.stripped_transactions = [mock_transaction_1, mock_transaction_2]

        level_2_actions.verify_transactions(mock_block, mock_keys, txn_map)
        self.assertTrue(txn_map["1"])
        self.assertIsNone(txn_map.get("2"))

    @patch("dragonchain.transaction_processor.level_2_actions.broadcast.dispatch")
    @patch("dragonchain.transaction_processor.level_2_actions.block_dao.insert_block")
    def test_send_data_inserts_and_dispatches(self, mock_insert_block, mock_dispatch):
        mock_block = MagicMock()
        level_2_actions.send_data(mock_block)

        mock_insert_block.assert_called_once_with(mock_block)
        mock_dispatch.assert_called_once_with(mock_block)

    @patch("dragonchain.transaction_processor.level_2_actions.get_verifying_keys", return_value="keys")
    @patch("dragonchain.transaction_processor.level_2_actions.verify_transactions")
    @patch("dragonchain.transaction_processor.level_2_actions.mark_invalid")
    @patch("dragonchain.transaction_processor.level_2_actions.verify_block", return_value=True)
    def test_process_transactions_verifies_if_valid_block(self, mock_verify_block, mock_invalidate, mock_validate, mock_get_keys):
        mock_block = MagicMock()
        self.assertEqual(level_2_actions.process_transactions(mock_block), {})

        mock_get_keys.assert_called_once()
        mock_verify_block.assert_called_once_with(mock_block, "keys")
        mock_invalidate.assert_not_called()
        mock_validate.assert_called_once_with(mock_block, "keys", {})

    @patch("dragonchain.transaction_processor.level_2_actions.get_verifying_keys", return_value="keys")
    @patch("dragonchain.transaction_processor.level_2_actions.verify_transactions")
    @patch("dragonchain.transaction_processor.level_2_actions.mark_invalid")
    @patch("dragonchain.transaction_processor.level_2_actions.verify_block", return_value=False)
    def test_process_transactions_invalidates_if_invalid_block(self, mock_verify_block, mock_invalidate, mock_validate, mock_get_keys):
        mock_block = MagicMock()
        self.assertEqual(level_2_actions.process_transactions(mock_block), {})

        mock_get_keys.assert_called_once()
        mock_verify_block.assert_called_once_with(mock_block, "keys")
        mock_invalidate.assert_called_once_with(mock_block, {})
        mock_validate.assert_not_called()

    @patch("dragonchain.transaction_processor.level_2_actions.get_verifying_keys", side_effect=RuntimeError)
    @patch("dragonchain.transaction_processor.level_2_actions.verify_transactions")
    @patch("dragonchain.transaction_processor.level_2_actions.mark_invalid")
    @patch("dragonchain.transaction_processor.level_2_actions.verify_block", return_value=False)
    def test_process_transactions_invalidates_if_no_matchmaking_data(self, mock_verify_block, mock_invalidate, mock_validate, mock_get_keys):
        mock_block = MagicMock()
        self.assertEqual(level_2_actions.process_transactions(mock_block), {})

        mock_get_keys.assert_called_once()
        mock_verify_block.assert_not_called()
        mock_invalidate.assert_called_once_with(mock_block, {})
        mock_validate.assert_not_called()

    def test_mark_invalid_marks_txns_bad(self):
        txn_map = {}
        mock_block = MagicMock()
        mock_transaction_one = '{"header": {"txn_id": "123"}}'
        mock_transaction_two = '{"header": {"txn_id": "124"}}'
        mock_block.stripped_transactions = [mock_transaction_one, mock_transaction_two]

        level_2_actions.mark_invalid(mock_block, txn_map)
        self.assertEqual(txn_map, {"123": False, "124": False})

    def test_mark_invalid_ignores_bad_json(self):
        txn_map = {}
        mock_block = MagicMock()
        mock_transaction_one = '{"header": {"txn_id": "123"}}'
        mock_transaction_two = "{header: {txn_id: 124}}"
        mock_block.stripped_transactions = [mock_transaction_one, mock_transaction_two]

        level_2_actions.mark_invalid(mock_block, txn_map)
        self.assertEqual(txn_map, {"123": False})

    @patch("dragonchain.transaction_processor.level_2_actions.party.get_address_ddss", return_value="3894723")
    @patch("dragonchain.transaction_processor.level_2_actions.keys.get_public_id")
    @patch("dragonchain.transaction_processor.level_2_actions.sign_block")
    @patch("dragonchain.transaction_processor.level_2_actions.get_next_block_info", return_value=(1, ""))
    def test_create_block_creates_and_signs_no_prev_proof(self, mock_get_next_info, mock_sign_block, mock_get_id, mock_registration):
        mock_block = MagicMock()
        response = level_2_actions.create_block(mock_block, {"1": True, "2": False, "3": True})

        mock_get_next_info.assert_called_once()
        mock_sign_block.assert_called_once()
        mock_registration.assert_called_once()
        self.assertEqual(response.current_ddss, "3894723")
        self.assertEqual(response.block_id, "1")
        self.assertEqual(response.prev_proof, "")
        self.assertEqual(response.validations_dict, {"1": True, "2": False, "3": True})
        self.assertIsInstance(response.proof, str)

    @patch("dragonchain.transaction_processor.level_2_actions.party.get_address_ddss", return_value="3894723")
    @patch("dragonchain.transaction_processor.level_2_actions.keys.get_public_id")
    @patch("dragonchain.transaction_processor.level_2_actions.sign_block")
    @patch("dragonchain.transaction_processor.level_2_actions.get_next_block_info", return_value=(1235, "MyProof"))
    def test_create_block_creates_and_signs_with_prev_proof(self, mock_get_proof, mock_sign, mock_get_id, mock_registration):
        mock_block = MagicMock()
        response = level_2_actions.create_block(mock_block, {"1": True, "2": False, "3": True})

        mock_get_proof.assert_called_once()
        mock_sign.assert_called_once()
        mock_registration.assert_called_once()
        self.assertEqual(response.current_ddss, "3894723")
        self.assertEqual(response.block_id, "1235")
        self.assertEqual(response.prev_proof, "MyProof")
        self.assertEqual(response.validations_dict, {"1": True, "2": False, "3": True})
        self.assertIsInstance(response.proof, str)

    @patch("dragonchain.transaction_processor.level_2_actions.block_dao.get_last_block_proof", return_value={"block_id": "1234", "proof": "MyProof"})
    def test_get_next_block_info_with_prev(self, mock_get_proof):
        block_id, prev_proof = level_2_actions.get_next_block_info()
        mock_get_proof.assert_called_once()
        self.assertEqual(block_id, 1235)
        self.assertEqual(prev_proof, "MyProof")

    @patch("dragonchain.transaction_processor.level_2_actions.block_dao.get_last_block_proof", return_value=None)
    @patch("dragonchain.transaction_processor.level_2_actions.shared_functions.sanity_check_empty_chain")
    def test_get_next_block_info_without_prev(self, mock_sanity_check, mock_get_proof):
        block_id, prev_proof = level_2_actions.get_next_block_info()
        mock_get_proof.assert_called_once()
        mock_sanity_check.assert_called_once()
        self.assertEqual(block_id, 1)
        self.assertEqual(prev_proof, "")

    @patch("dragonchain.transaction_processor.level_2_actions.keys.get_my_keys")
    @patch("dragonchain.transaction_processor.level_2_actions.PROOF_SCHEME", "work")
    def test_sign_block_does_pow(self, mock_keys):
        mock_keys.return_value = MagicMock(pow_block=MagicMock(return_value=("proof", "nonce")))
        mock_block = MagicMock()
        level_2_actions.sign_block(mock_block)

        mock_keys.return_value.pow_block.assert_called_once_with(mock_block)
        self.assertEqual(mock_block.proof, "proof")
        self.assertEqual(mock_block.nonce, "nonce")

    @patch("dragonchain.transaction_processor.level_2_actions.keys.get_my_keys")
    @patch("dragonchain.transaction_processor.level_2_actions.PROOF_SCHEME", "trust")
    def test_sign_block_does_trust(self, mock_keys):
        mock_keys.return_value = MagicMock(sign_block=MagicMock(return_value="proof"))
        mock_block = MagicMock()
        level_2_actions.sign_block(mock_block)

        mock_keys.return_value.sign_block.assert_called_once_with(mock_block)
        self.assertEqual(mock_block.proof, "proof")

    @patch("dragonchain.transaction_processor.level_2_actions.queue.is_not_empty", return_value=True)
    @patch("dragonchain.transaction_processor.level_2_actions.execute")
    def test_recurse_necessary(self, mock_execute, mock_is_not_empty):
        level_2_actions.recurse_if_necessary()

        mock_execute.assert_called_once()

    @patch("dragonchain.transaction_processor.level_2_actions.queue.is_not_empty", return_value=False)
    @patch("dragonchain.transaction_processor.level_2_actions.execute")
    def test_recurse_not_necessary(self, mock_execute, mock_is_not_empty):
        level_2_actions.recurse_if_necessary()

        mock_execute.assert_not_called()

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
from dragonchain.transaction_processor import level_3_actions


class TestLevelThreeActions(unittest.TestCase):
    @patch("dragonchain.transaction_processor.level_3_actions.matchmaking")
    @patch("dragonchain.transaction_processor.level_3_actions.send_data")
    @patch("dragonchain.transaction_processor.level_3_actions.recurse_if_necessary")
    @patch("dragonchain.transaction_processor.level_3_actions.create_block")
    @patch("dragonchain.transaction_processor.level_3_actions.verify_blocks", return_value=(MagicMock(), MagicMock(), MagicMock(), MagicMock()))
    @patch("dragonchain.transaction_processor.level_3_actions.get_new_blocks", return_value=(MagicMock(), MagicMock()))
    @patch("dragonchain.transaction_processor.level_3_actions.clear_processing_blocks")
    def test_execute_calls_correct_functions(
        self, mock_clear_processing, mock_get_block, mock_verify_blocks, mock_create_block, mock_recurse, mock_send_data, mock_matchmaking
    ):
        level_3_actions.execute()

        mock_get_block.assert_called_once()
        mock_verify_blocks.assert_called_once()
        mock_create_block.assert_called_once()
        mock_send_data.assert_called_once()
        mock_recurse.assert_called_once()
        mock_clear_processing.assert_called_once()

    @patch("dragonchain.transaction_processor.level_3_actions.matchmaking")
    @patch("dragonchain.transaction_processor.level_3_actions.send_data")
    @patch("dragonchain.transaction_processor.level_3_actions.recurse_if_necessary")
    @patch("dragonchain.transaction_processor.level_3_actions.create_block")
    @patch("dragonchain.transaction_processor.level_3_actions.verify_blocks", return_value=(MagicMock(), MagicMock(), MagicMock(), MagicMock()))
    @patch("dragonchain.transaction_processor.level_3_actions.get_new_blocks", return_value=(None, None))
    @patch("dragonchain.transaction_processor.level_3_actions.clear_processing_blocks")
    def test_execute_no_ops_on_empty_queue(
        self, mock_clear_processing, mock_get_block, mock_verify_blocks, mock_create_block, mock_recurse, mock_send_data, mock_matchmaking
    ):
        level_3_actions.execute()

        mock_get_block.assert_called_once()

        mock_verify_blocks.assert_not_called()
        mock_create_block.assert_not_called()
        mock_send_data.assert_not_called()
        mock_recurse.assert_not_called()
        mock_clear_processing.assert_not_called()

    @patch("dragonchain.transaction_processor.level_3_actions.clear_processing_blocks")
    @patch("dragonchain.transaction_processor.level_3_actions.matchmaking")
    @patch("dragonchain.transaction_processor.level_3_actions.recurse_if_necessary")
    @patch("dragonchain.transaction_processor.level_3_actions.verify_blocks", return_value=(MagicMock(), 0, MagicMock(), MagicMock()))
    @patch("dragonchain.transaction_processor.level_3_actions.get_new_blocks", return_value=({"dc_id": "123", "block_id": "123"}, True))
    def test_execute_skips_on_invalid_block(self, mock_get_block, mock_verify_blocks, mock_recurse, mock_matchmaking, mock_clear_blocks):
        level_3_actions.execute()

        mock_get_block.assert_called_once()
        mock_verify_blocks.assert_called_once()
        mock_recurse.assert_called_once()
        mock_clear_blocks.assert_called_once()

    @patch("dragonchain.transaction_processor.level_3_actions.broadcast.dispatch")
    @patch("dragonchain.transaction_processor.level_3_actions.block_dao.insert_block")
    def test_send_data_inserts_and_dispatches(self, mock_insert_block, mock_dispatch):
        mock_block = MagicMock()
        level_3_actions.send_data(mock_block)
        mock_insert_block.assert_called_once_with(mock_block)

        mock_dispatch.assert_called_once_with(mock_block)

    @patch("dragonchain.transaction_processor.level_3_actions.get_verifying_keys", return_value=MagicMock(verify_block=MagicMock(return_value=True)))
    @patch(
        "dragonchain.transaction_processor.level_3_actions.matchmaking.get_registration",
        return_value={"cloud": "aws", "region": "us-west-2", "wallet": "walletAddress"},
    )
    def test_verify_block_returns_data_on_valid_block(self, mock_registration, mock_get_keys):
        mock_block = MagicMock(dc_id=123, block_id=124, current_ddss="123432")
        clouds, regions, ddss, l2_count = level_3_actions.verify_block(mock_block, set(), set(), 0, 0)
        mock_get_keys.assert_called_once_with(123)
        mock_registration.assert_called_once_with(123)
        self.assertEqual(clouds, {"aws"})
        self.assertEqual(regions, {"us-west-2"})
        self.assertEqual(ddss, 123432)
        self.assertEqual(l2_count, 1)

    @patch("dragonchain.transaction_processor.level_3_actions.matchmaking.get_registration")
    @patch("dragonchain.transaction_processor.level_3_actions.get_verifying_keys", side_effect=RuntimeError)
    def test_verify_block_returns_inputted_data_on_unverifiable_block(self, mock_get_keys, mock_registration):
        mock_block = MagicMock(dc_id=123, block_id=124)
        clouds, regions, ddss, l2_count = level_3_actions.verify_block(mock_block, set(), set(), 0, 0)
        mock_get_keys.assert_called_once_with(123)
        mock_registration.assert_not_called()
        self.assertEqual(clouds, set())
        self.assertEqual(regions, set())
        self.assertEqual(ddss, 0)
        self.assertEqual(l2_count, 0)

    @patch("dragonchain.transaction_processor.level_3_actions.matchmaking.get_registration")
    @patch("dragonchain.transaction_processor.level_3_actions.get_verifying_keys", return_value=MagicMock(verify_block=MagicMock(return_value=False)))
    def test_verify_block_returns_what_was_passed_in_on_invalid_block(self, mock_get_keys, mock_registration):
        mock_block = MagicMock(dc_id=123, block_id=123)
        clouds, regions, ddss, l2_count = level_3_actions.verify_block(mock_block, set(), set(), 0, 0)
        mock_get_keys.assert_called_once_with(123)
        mock_registration.assert_not_called()
        self.assertEqual(clouds, set())
        self.assertEqual(regions, set())
        self.assertEqual(ddss, 0)
        self.assertEqual(l2_count, 0)

    @patch("dragonchain.transaction_processor.level_3_actions.queue.check_and_recover_processing_if_necessary")
    @patch("dragonchain.transaction_processor.level_3_actions.queue.get_next_l2_blocks")
    def test_get_new_blocks_calls_incoming_queue(self, mock_get_blocks, mock_recover):
        level_3_actions.get_new_blocks()
        mock_get_blocks.assert_called_once()

    @patch("dragonchain.transaction_processor.level_3_actions.queue.check_and_recover_processing_if_necessary")
    @patch("dragonchain.transaction_processor.level_3_actions.queue.get_next_l2_blocks")
    def test_get_new_blocks_checks_for_recovery(self, mock_get_blocks, mock_recover):
        level_3_actions.get_new_blocks()
        mock_recover.assert_called_once()

    @patch("dragonchain.transaction_processor.level_3_actions.keys.DCKeys", return_value="ChainKeys")
    def test_get_verifying_keys_returns_correct_keys(self, mock_keys):
        self.assertEqual(level_3_actions.get_verifying_keys("MyID"), "ChainKeys")
        mock_keys.assert_called_once_with("MyID")

    @patch("dragonchain.transaction_processor.level_3_actions.party.get_address_ddss", return_value="3894723")
    @patch("dragonchain.transaction_processor.level_3_actions.keys.get_public_id")
    @patch("dragonchain.transaction_processor.level_3_actions.sign_block")
    @patch("dragonchain.transaction_processor.level_3_actions.get_next_block_info", return_value=(1, ""))
    def test_create_block_creates_and_signs_no_prev_proof(self, mock_get_block_info, mock_sign, mock_get_public_id, mock_registration):
        mock_l2_proof = MagicMock()
        mock_l2_proof.dc_id = "banana"
        mock_l2_proof.block_id = "4"
        mock_l2_proof.proof = "bananaproof"
        response = level_3_actions.create_block({"dc_id": "1", "block_id": "1", "proof": "myproof"}, 100, 20, ["us-west-2"], ["aws"], [mock_l2_proof])

        mock_get_public_id.assert_called()
        mock_sign.assert_called_once()
        mock_registration.assert_called_once()
        self.assertEqual(response.current_ddss, "3894723")
        self.assertEqual(response.block_id, "1")
        self.assertEqual(response.prev_proof, "")
        self.assertEqual(response.ddss, "100")
        self.assertEqual(response.clouds, ["aws"])
        self.assertEqual(response.regions, ["us-west-2"])
        self.assertEqual(response.l2_proofs, [{"dc_id": "banana", "block_id": "4", "proof": "bananaproof"}])
        self.assertIsInstance(response.proof, str)

    @patch("dragonchain.transaction_processor.level_3_actions.party.get_address_ddss", return_value="3894723")
    @patch("dragonchain.transaction_processor.level_3_actions.keys.get_public_id")
    @patch("dragonchain.transaction_processor.level_3_actions.sign_block")
    @patch("dragonchain.transaction_processor.level_3_actions.get_next_block_info", return_value=(1235, "MyProof"))
    def test_create_block_creates_and_signs_with_prev_proof(self, mock_get_block_info, mock_sign, mock_get_public_id, mock_registration):
        mock_l2_proof = MagicMock()
        mock_l2_proof.dc_id = "banana"
        mock_l2_proof.block_id = "4"
        mock_l2_proof.proof = "bananaproof"
        response = level_3_actions.create_block({"dc_id": "1", "block_id": "1", "proof": "myproof"}, 100, 20, ["us-west-2"], ["aws"], [mock_l2_proof])

        mock_sign.assert_called_once()
        mock_get_public_id.assert_called()
        mock_registration.assert_called_once()
        self.assertEqual(response.current_ddss, "3894723")
        self.assertEqual(response.block_id, "1235")
        self.assertEqual(response.prev_proof, "MyProof")
        self.assertEqual(response.ddss, "100")
        self.assertEqual(response.clouds, ["aws"])
        self.assertEqual(response.regions, ["us-west-2"])
        self.assertEqual(response.l2_proofs, [{"dc_id": "banana", "block_id": "4", "proof": "bananaproof"}])
        self.assertIsInstance(response.proof, str)

    @patch("dragonchain.transaction_processor.level_3_actions.block_dao.get_last_block_proof", return_value={"block_id": "1234", "proof": "MyProof"})
    def test_get_next_block_info_with_prev(self, mock_get_proof):
        block_id, prev_proof = level_3_actions.get_next_block_info()
        mock_get_proof.assert_called_once()
        self.assertEqual(block_id, 1235)
        self.assertEqual(prev_proof, "MyProof")

    @patch("dragonchain.transaction_processor.level_3_actions.block_dao.get_last_block_proof", return_value=None)
    @patch("dragonchain.transaction_processor.level_3_actions.shared_functions.sanity_check_empty_chain")
    def test_get_next_block_info_without_prev(self, mock_sanity_check, mock_get_proof):
        block_id, prev_proof = level_3_actions.get_next_block_info()
        mock_get_proof.assert_called_once()
        mock_sanity_check.assert_called_once()
        self.assertEqual(block_id, 1)
        self.assertEqual(prev_proof, "")

    @patch("dragonchain.transaction_processor.level_3_actions.keys.get_my_keys")
    @patch("dragonchain.transaction_processor.level_3_actions.PROOF_SCHEME", "work")
    def test_sign_block_does_pow(self, mock_keys):
        mock_keys.return_value = MagicMock(pow_block=MagicMock(return_value=("proof", "nonce")))
        mock_block = MagicMock()
        level_3_actions.sign_block(mock_block)

        mock_keys.return_value.pow_block.assert_called_once_with(mock_block)
        self.assertEqual(mock_block.proof, "proof")
        self.assertEqual(mock_block.nonce, "nonce")

    @patch("dragonchain.transaction_processor.level_3_actions.keys.get_my_keys")
    @patch("dragonchain.transaction_processor.level_3_actions.PROOF_SCHEME", "trust")
    def test_sign_block_does_trust(self, mock_keys):
        mock_keys.return_value = MagicMock(sign_block=MagicMock(return_value="proof"))
        mock_block = MagicMock()
        level_3_actions.sign_block(mock_block)

        mock_keys.return_value.sign_block.assert_called_once_with(mock_block)
        self.assertEqual(mock_block.proof, "proof")

    @patch("dragonchain.transaction_processor.level_3_actions.queue.is_not_empty", return_value=True)
    @patch("dragonchain.transaction_processor.level_3_actions.execute")
    def test_recurse_necessary(self, mock_execute, mock_is_not_empty):
        level_3_actions.recurse_if_necessary()

        mock_execute.assert_called_once()

    @patch("dragonchain.transaction_processor.level_3_actions.queue.is_not_empty", return_value=False)
    @patch("dragonchain.transaction_processor.level_3_actions.execute")
    def test_recurse_not_necessary(self, mock_execute, mock_is_not_empty):
        level_3_actions.recurse_if_necessary()

        mock_execute.assert_not_called()

    @patch("dragonchain.transaction_processor.level_3_actions.verify_block", return_value=({"aws"}, {"us-west-2"}, 200, 2))
    def test_keys_verifys_blocks(self, mock_verify):
        mock_block = MagicMock(l1_dc_id="1", l1_block_id="1", l1_proof="MyProof")
        headers = {"dc_id": "1", "block_id": "1", "proof": "MyProof"}

        mock_blocks = [mock_block, mock_block]

        ddss, l2_count, regions, clouds = level_3_actions.verify_blocks(mock_blocks, headers)
        mock_verify.assert_called_once_with(mock_block, set(), set(), 0, 0)
        self.assertEqual(ddss, 200)
        self.assertEqual(l2_count, 2)
        self.assertEqual(regions, ["us-west-2"])
        self.assertEqual(clouds, ["aws"])

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
from time import time
import unittest
from unittest.mock import patch, MagicMock, call, ANY

from dragonchain import test_env  # noqa: F401
from dragonchain.transaction_processor import level_5_actions
from dragonchain import exceptions


class TestLevelFiveActions(unittest.TestCase):
    matchmaking_mock = {
        "network": "eth",
        "funded": True,
        "broadcastInterval": 2,
        "interchainWallet": "0xwallet",
        "wallet": "0xWallet",
        "ddss": "5000",
    }
    fake_l5_block = {
        "version": "1",
        "dcrn": "Block::L5::AtRest",
        "header": {"dc_id": "2", "block_id": "3", "level": 4, "timestamp": "123452", "prev_proof": "myproof"},
        "proof": {"proof": "moreproof", "scheme": "trust", "transaction_hash": ["0xTxnHash"], "network": "eth", "block_last_sent_at": "234235"},
        "l4-blocks": ["some blocks"],
    }

    def setUp(self):
        os.environ["LEVEL"] = "5"
        level_5_actions.BROADCAST_INTERVAL = 7200
        level_5_actions.INTERCHAIN_NETWORK = "eth"
        level_5_actions.FUNDED = True
        level_5_actions._interchain_client = MagicMock()

    def tearDown(self):
        os.environ["LEVEL"] = "1"

    @patch("dragonchain.transaction_processor.level_5_actions.matchmaking.get_matchmaking_config", return_value=matchmaking_mock)
    @patch("dragonchain.transaction_processor.level_5_actions.interchain_dao.get_default_interchain_client", return_value="thing")
    def test_set_up_sets_module_state_properly(self, mock_interchain, mock_get_config):
        level_5_actions.setup()
        self.assertEqual(level_5_actions.BROADCAST_INTERVAL, 7200)
        self.assertEqual(level_5_actions.INTERCHAIN_NETWORK, "eth")
        self.assertTrue(level_5_actions.FUNDED)
        self.assertEqual(level_5_actions._interchain_client, "thing")
        mock_get_config.assert_called_once()

    @patch("dragonchain.transaction_processor.level_5_actions.matchmaking")
    @patch("dragonchain.transaction_processor.level_5_actions.check_confirmations")
    @patch("dragonchain.transaction_processor.level_5_actions.should_broadcast", return_value=False)
    @patch("dragonchain.transaction_processor.level_5_actions.store_l4_blocks")
    @patch("dragonchain.transaction_processor.level_5_actions.get_last_block_number", return_value="123")
    @patch("dragonchain.transaction_processor.level_5_actions.has_funds_for_transactions", return_value=True)
    def test_execute_calls_correct_functions_when_funded_but_not_time_to_broadcast(
        self, mock_has_funds, mock_get_last_block, mock_store, mock_should_broadcast, mock_confirmations, mock_matchmaking
    ):
        level_5_actions.execute()

        mock_has_funds.assert_called_once()
        mock_get_last_block.assert_called_once()
        mock_store.assert_called_once()
        mock_should_broadcast.assert_called_once()
        mock_confirmations.assert_called_once()

    @patch("dragonchain.transaction_processor.level_5_actions.matchmaking")
    @patch("dragonchain.transaction_processor.level_5_actions.check_confirmations")
    @patch("dragonchain.transaction_processor.level_5_actions.watch_for_funds")
    @patch("dragonchain.transaction_processor.level_5_actions.broadcast_clean_up")
    @patch("dragonchain.transaction_processor.level_5_actions.broadcast_to_public_chain")
    @patch("dragonchain.transaction_processor.level_5_actions.create_l5_block")
    @patch("dragonchain.transaction_processor.level_5_actions.should_broadcast", return_value=True)
    @patch("dragonchain.transaction_processor.level_5_actions.store_l4_blocks")
    @patch("dragonchain.transaction_processor.level_5_actions.get_last_block_number", return_value="123")
    @patch("dragonchain.transaction_processor.level_5_actions.has_funds_for_transactions", return_value=True)
    def test_execute_calls_correct_functions_when_funded_and_time_to_broadcast(
        self,
        mock_has_funds,
        mock_get_last_block,
        mock_store,
        mock_should_broadcast,
        mock_create_l5,
        mock_broadcast,
        mock_broadcast_cleanup,
        mock_watch_for_funds,
        mock_confirmations,
        mock_matchmaking,
    ):
        level_5_actions.execute()

        mock_has_funds.assert_called_once()
        mock_get_last_block.assert_called_once()
        mock_store.assert_called_once()
        mock_should_broadcast.assert_called_once()
        mock_create_l5.assert_called_once()
        mock_broadcast.assert_called_once()
        mock_broadcast_cleanup.assert_called_once()
        mock_watch_for_funds.assert_called_once()
        mock_confirmations.assert_called_once()

    @patch("dragonchain.transaction_processor.level_5_actions.matchmaking")
    @patch("dragonchain.transaction_processor.level_5_actions.check_confirmations")
    @patch("dragonchain.transaction_processor.level_5_actions.watch_for_funds")
    @patch("dragonchain.transaction_processor.level_5_actions.is_time_to_watch", return_value=True)
    @patch("dragonchain.transaction_processor.level_5_actions.has_funds_for_transactions", return_value=False)
    def test_execute_calls_correct_functions_when_out_of_funds(
        self, mock_has_funds, mock_is_time_to_watch, mock_watch, mock_confirmations, mock_matchmaking
    ):
        level_5_actions.execute()

        mock_has_funds.assert_called_once()
        mock_is_time_to_watch.assert_called_once()
        mock_watch.assert_called_once()
        mock_confirmations.assert_called_once()

    @patch("dragonchain.transaction_processor.level_5_actions.storage.delete_directory")
    @patch("dragonchain.transaction_processor.level_5_actions.set_last_block_number")
    @patch("dragonchain.transaction_processor.level_5_actions.set_last_broadcast_time")
    def test_broadcast_cleanup_calls_correct_functions(self, mock_set_broadcast_time, mock_set_block, mock_delete_directory):
        mock_block = MagicMock(block_id="123")
        level_5_actions.broadcast_clean_up(mock_block)

        mock_set_broadcast_time.assert_called_once()
        mock_set_block.assert_called_once_with("123")
        mock_delete_directory.assert_called_once_with("BROADCAST/TO_BROADCAST/123")

    @patch("dragonchain.transaction_processor.level_5_actions.queue.check_and_recover_processing_if_necessary")
    @patch("dragonchain.transaction_processor.level_5_actions.queue.get_new_l4_blocks")
    @patch("dragonchain.transaction_processor.level_5_actions.queue.clear_processing_queue")
    @patch("dragonchain.transaction_processor.level_5_actions.storage.put_object_as_json")
    @patch("dragonchain.transaction_processor.level_5_actions.verify_blocks", return_value="verified_blocks")
    def test_store_l4_blocks(self, mock_verify_blocks, mock_storage_put, mock_clear, mock_get_blocks, mock_recover):
        level_5_actions.store_l4_blocks(5)

        mock_recover.assert_called_once()
        mock_get_blocks.assert_called_once()
        mock_clear.assert_called_once()
        mock_verify_blocks.assert_called_once()
        mock_storage_put.assert_called_once()

    @patch("dragonchain.transaction_processor.level_5_actions.verify_block", return_value="verified_record")
    def test_verify_blocks_verifies_each(self, mock_verify):
        mock_l4_blocks = ['{"l4-blocks": ["testblock", "testblock2"]}', '{"l4-blocks": ["testblock3", "testblock4"]}']
        verifications = level_5_actions.verify_blocks(mock_l4_blocks)

        self.assertEqual(len(verifications), 4)
        mock_verify.assert_has_calls([call("testblock"), call("testblock2"), call("testblock3"), call("testblock4")])

    def test_verify_block_marks_invalid_block(self):
        l4_block = {"invalid!!": "this aint valid"}
        l4_block = level_5_actions.verify_block(l4_block)

        self.assertTrue(l4_block.get("is_invalid"))

    def test_verify_block_validates_block_schema(self):
        fake_l4_block = {
            "version": "1",
            "dcrn": "Block::L4::AtRest",
            "header": {
                "dc_id": "43",
                "level": 4,
                "block_id": "23",
                "timestamp": "123445235",
                "l1_dc_id": "32",
                "l1_block_id": "423",
                "l1_proof": "proofity proof",
                "prev_proof": "some_more_proooof",
            },
            "l3-validations": [{"l3_dc_id": "1", "l3_block_id": "2", "l3_proof": "prooof", "valid": True}],
            "proof": {"scheme": "trust", "proof": "some_proof"},
        }
        l4_block = level_5_actions.verify_block(fake_l4_block)

        self.assertIsNone(l4_block.get("is_invalid"))
        self.assertEqual(l4_block, fake_l4_block)

    @patch("dragonchain.transaction_processor.level_5_actions.storage.put_object_as_json")
    @patch("dragonchain.transaction_processor.level_5_actions.keys.get_my_keys")
    @patch("dragonchain.transaction_processor.level_5_actions.redisearch.put_document")
    def test_broadcast_to_public_chain(self, mock_put_document, mock_keys, mock_storage_put):
        mock_keys.return_value = MagicMock(hash_l5_for_public_broadcast=MagicMock(return_value="PoE"))
        mock_block = MagicMock(transaction_hash=[], block_id="123")
        level_5_actions._interchain_client.publish_l5_hash_to_public_network = MagicMock(return_value="0xTransactionHash")
        level_5_actions._interchain_client.get_current_block = MagicMock(return_value=8754)

        level_5_actions.broadcast_to_public_chain(mock_block)

        mock_keys.assert_called_once_with()
        level_5_actions._interchain_client.publish_l5_hash_to_public_network.assert_called_once_with("PoE")
        mock_storage_put.assert_called_once_with("BLOCK/123", ANY)
        mock_put_document.assert_called_once_with("bk", "123", ANY, upsert=True)
        self.assertEqual(mock_block.transaction_hash, ["0xTransactionHash"])
        self.assertEqual(mock_block.block_last_sent_at, 8754)
        self.assertEqual(mock_block.network, "eth")

    @patch("dragonchain.transaction_processor.level_5_actions.get_last_confirmed_block", return_value={"block_id": "123"})
    @patch("dragonchain.transaction_processor.level_5_actions.get_last_block_number", return_value="124")
    @patch("dragonchain.transaction_processor.level_5_actions.finalize_block")
    @patch("dragonchain.transaction_processor.level_5_actions.storage.get_json_from_object", return_value=fake_l5_block)
    def test_check_confirmations_finalizes_when_confirmed(self, mock_storage_get, mock_finalize, mock_get_last_number, mock_get_last_confirmed):
        level_5_actions._interchain_client.is_transaction_confirmed.return_value = True

        level_5_actions.check_confirmations()

        mock_get_last_number.assert_called_once()
        mock_get_last_confirmed.assert_called_once()
        mock_finalize.assert_called_once()
        mock_storage_get.assert_called_once_with("BLOCK/124")
        level_5_actions._interchain_client.should_retry_broadcast.assert_not_called()

    @patch("dragonchain.transaction_processor.level_5_actions.get_last_confirmed_block", return_value={"block_id": "123"})
    @patch("dragonchain.transaction_processor.level_5_actions.get_last_block_number", return_value="124")
    @patch("dragonchain.transaction_processor.level_5_actions.finalize_block")
    @patch("dragonchain.transaction_processor.level_5_actions.storage.get_json_from_object", return_value=fake_l5_block)
    @patch("dragonchain.transaction_processor.level_5_actions.broadcast_to_public_chain")
    @patch("dragonchain.transaction_processor.level_5_actions.l5_block_model.new_from_at_rest")
    def test_check_confirmations_removes_unneeded_hashes(
        self, mock_block_model, mock_retry, mock_storage_get, mock_finalize, mock_get_last_number, mock_get_last_confirmed
    ):
        level_5_actions._interchain_client.is_transaction_confirmed.side_effect = exceptions.TransactionNotFound
        mock_block_model.return_value.transaction_hash = ["1"]

        level_5_actions.check_confirmations()

        mock_get_last_number.assert_called_once()
        mock_get_last_confirmed.assert_called_once()
        mock_finalize.assert_not_called()
        mock_storage_get.assert_called_once_with("BLOCK/124")
        self.assertEqual(mock_block_model.return_value.transaction_hash, [])

    @patch("dragonchain.transaction_processor.level_5_actions.get_last_confirmed_block", return_value={"block_id": "123"})
    @patch("dragonchain.transaction_processor.level_5_actions.get_last_block_number", return_value="124")
    @patch("dragonchain.transaction_processor.level_5_actions.finalize_block")
    @patch("dragonchain.transaction_processor.level_5_actions.storage.get_json_from_object", return_value=fake_l5_block)
    @patch("dragonchain.transaction_processor.level_5_actions.broadcast_to_public_chain")
    def test_check_confirmations_attempts_to_retry_when_not_confirmed(
        self, mock_retry, mock_storage_get, mock_finalize, mock_get_last_number, mock_get_last_confirmed
    ):
        level_5_actions._interchain_client.is_transaction_confirmed.return_value = False

        level_5_actions.check_confirmations()

        mock_get_last_number.assert_called_once()
        mock_get_last_confirmed.assert_called_once()
        mock_storage_get.assert_called_once_with("BLOCK/124")
        mock_finalize.assert_not_called()
        mock_retry.assert_called_once()

    @patch("dragonchain.transaction_processor.level_5_actions.get_last_confirmed_block", return_value={"block_id": "124"})
    @patch("dragonchain.transaction_processor.level_5_actions.get_last_block_number", return_value="124")
    @patch("dragonchain.transaction_processor.level_5_actions.finalize_block")
    @patch("dragonchain.transaction_processor.level_5_actions.storage.get_json_from_object")
    @patch("dragonchain.transaction_processor.level_5_actions.broadcast_to_public_chain")
    def test_check_confirmations_noops_when_no_blocks_to_confirm(
        self, mock_retry, mock_storage_get, mock_finalize, mock_get_last_number, mock_get_last_confirmed
    ):
        level_5_actions._interchain_client.is_transaction_confirmed.return_value = True

        level_5_actions.check_confirmations()

        mock_get_last_number.assert_called_once()
        mock_get_last_confirmed.assert_called_once()
        mock_storage_get.assert_not_called()
        mock_finalize.assert_not_called()
        mock_retry.assert_not_called()

    @patch("dragonchain.transaction_processor.level_5_actions.storage.put_object_as_json")
    @patch("dragonchain.transaction_processor.level_5_actions.broadcast.dispatch")
    @patch("dragonchain.transaction_processor.level_5_actions.keys.get_my_keys")
    @patch("dragonchain.transaction_processor.level_5_actions.set_last_confirmed_block")
    def test_finalize_block_calls_correct_actions(self, mock_set_last_confirmed, mock_keys, mock_dispatch, mock_put_json):
        mock_keys.return_value = MagicMock(sign_block=MagicMock(return_value="MyProof"))
        mock_block = MagicMock(block_id="1234")
        level_5_actions.finalize_block(mock_block, {"proof": {"proof": "MyLastProof"}}, "0xTransactionHash")

        mock_set_last_confirmed.assert_called_once_with(mock_block)
        mock_dispatch.assert_called_once_with(mock_block)
        mock_keys.return_value.sign_block.assert_called_once_with(mock_block)
        mock_put_json.assert_called_once()

        self.assertEqual(mock_block.proof, "MyProof")
        self.assertEqual(mock_block.prev_proof, "MyLastProof")
        self.assertEqual(mock_block.transaction_hash, ["0xTransactionHash"])

    @patch("dragonchain.transaction_processor.level_5_actions.storage.get", side_effect=exceptions.NotFound)
    @patch("dragonchain.transaction_processor.level_5_actions.shared_functions.sanity_check_empty_chain")
    def test_get_last_block_number_returns_zero_on_new_chain(self, mock_sanity_check, mock_storage_get):
        response = level_5_actions.get_last_block_number()

        mock_sanity_check.assert_called_once()
        mock_storage_get.assert_called_once_with("BROADCAST/LAST_BLOCK")
        self.assertEqual(response, "0")

    @patch("dragonchain.transaction_processor.level_5_actions.storage.get", return_value=b"500")
    @patch("dragonchain.transaction_processor.level_5_actions.shared_functions.sanity_check_empty_chain")
    def test_get_last_block_number_returns_correctly(self, mock_sanity_check, mock_storage_get):
        response = level_5_actions.get_last_block_number()

        mock_sanity_check.assert_not_called()
        mock_storage_get.assert_called_once_with("BROADCAST/LAST_BLOCK")
        self.assertEqual(response, "500")

    @patch(
        "dragonchain.transaction_processor.level_5_actions.storage.get_json_from_object",
        return_value={"block_id": "500", "proof": {"proof": "myProof", "scheme": "trust"}},
    )
    def test_get_last_confirmed_block(self, mock_storage_get):
        response = level_5_actions.get_last_confirmed_block()

        mock_storage_get.assert_called_once_with("BROADCAST/LAST_CONFIRMED_BLOCK")
        self.assertEqual(response, {"block_id": "500", "proof": {"proof": "myProof", "scheme": "trust"}})

    @patch("dragonchain.transaction_processor.level_5_actions.storage.get_json_from_object", side_effect=exceptions.NotFound)
    def test_get_last_confirmed_block_returns_new_stub_on_new_chain(self, mock_storage_get):
        response = level_5_actions.get_last_confirmed_block()

        mock_storage_get.assert_called_once_with("BROADCAST/LAST_CONFIRMED_BLOCK")
        self.assertEqual(response, {"block_id": "0", "proof": {}})

    @patch("dragonchain.transaction_processor.level_5_actions.storage.put")
    def test_set_last_block_calls_storage_correctly(self, mock_storage_put):
        level_5_actions.set_last_block_number("50")
        mock_storage_put.assert_called_once_with("BROADCAST/LAST_BLOCK", b"50")

    @patch("dragonchain.transaction_processor.level_5_actions.storage.put_object_as_json")
    def test_set_last_confirmed_block_calls_storage_correctly(self, mock_storage_put):
        mock_block = MagicMock(block_id="50", export_as_at_rest=MagicMock(return_value={"proof": "MyProof"}))
        level_5_actions.set_last_confirmed_block(mock_block)
        mock_storage_put.assert_called_once_with("BROADCAST/LAST_CONFIRMED_BLOCK", {"block_id": "50", "proof": "MyProof"})

    @patch("dragonchain.transaction_processor.level_5_actions.storage.get", return_value=b"54354345")
    def test_get_last_broadcast_time_calls_storage_correctly(self, mock_storage_get):
        self.assertEqual(level_5_actions.get_last_broadcast_time(), 54354345)
        mock_storage_get.assert_called_once_with("BROADCAST/LAST_BROADCAST_TIME")

    @patch("dragonchain.transaction_processor.level_5_actions.storage.get", return_value=b"54354345")
    def test_get_last_watch_time_calls_storage_correctly(self, mock_storage_get):
        self.assertEqual(level_5_actions.get_last_watch_time(), 54354345)
        mock_storage_get.assert_called_once_with("BROADCAST/LAST_WATCH_TIME")

    @patch("dragonchain.transaction_processor.level_5_actions.storage.put")
    def test_set_last_broadcast_time_calls_storage_correctly(self, mock_storage_put):
        level_5_actions.set_last_broadcast_time()
        mock_storage_put.assert_called_once_with("BROADCAST/LAST_BROADCAST_TIME", ANY)

    @patch("dragonchain.transaction_processor.level_5_actions.storage.put")
    def test_set_last_watch_time_calls_storage_correctly(self, mock_storage_put):
        level_5_actions.set_last_watch_time()
        mock_storage_put.assert_called_once_with("BROADCAST/LAST_WATCH_TIME", ANY)

    @patch("dragonchain.transaction_processor.level_5_actions.storage.put")
    def test_set_funds_calls_storage_correctly(self, mock_storage_put):
        level_5_actions.set_funds("123452453425")
        mock_storage_put.assert_called_once_with("BROADCAST/CURRENT_FUNDS", b"123452453425")

    @patch("dragonchain.transaction_processor.level_5_actions.get_last_broadcast_time", side_effect=exceptions.NotFound)
    @patch("dragonchain.transaction_processor.level_5_actions.set_last_broadcast_time")
    def test_should_broadcast_returns_false_if_never_set(self, mock_set, mock_get):
        self.assertFalse(level_5_actions.should_broadcast("2343"))
        mock_get.assert_called_once()
        mock_set.assert_called_once()

    @patch("dragonchain.transaction_processor.level_5_actions.get_last_broadcast_time", return_value=(int(time()) - 60))
    def test_should_broadcast_returns_false_if_not_time(self, mock_get):
        self.assertFalse(level_5_actions.should_broadcast("2343"))
        mock_get.assert_called_once()

    @patch("dragonchain.transaction_processor.level_5_actions.get_last_broadcast_time", return_value=0)
    @patch("dragonchain.transaction_processor.level_5_actions.is_backlog", return_value=True)
    def test_should_broadcast_returns_true_if_time_and_backlog(self, mock_is_backlog, mock_get):
        self.assertTrue(level_5_actions.should_broadcast("2343"))
        mock_get.assert_called_once()
        mock_is_backlog.assert_called_once_with("2343")

    @patch("dragonchain.transaction_processor.level_5_actions.get_last_broadcast_time", return_value=0)
    @patch("dragonchain.transaction_processor.level_5_actions.is_backlog", return_value=False)
    @patch("dragonchain.transaction_processor.level_5_actions.set_last_broadcast_time", return_value=False)
    def test_should_broadcast_returns_false_if_time_and_no_backlog(self, mock_set, mock_is_backlog, mock_get):
        self.assertFalse(level_5_actions.should_broadcast("2343"))
        mock_get.assert_called_once()
        mock_is_backlog.assert_called_once_with("2343")
        mock_set.assert_called_once()

    @patch("dragonchain.transaction_processor.level_5_actions.get_last_watch_time", side_effect=exceptions.NotFound)
    @patch("dragonchain.transaction_processor.level_5_actions.set_last_watch_time")
    def test_is_time_to_watch_returns_true_if_never_watched(self, mock_set, mock_get):
        self.assertTrue(level_5_actions.is_time_to_watch())
        mock_get.assert_called_once()
        mock_set.assert_called_once()

    @patch("dragonchain.transaction_processor.level_5_actions.get_last_watch_time", return_value=0)
    def test_is_time_to_watch_returns_true_if_time(self, mock_get):
        self.assertTrue(level_5_actions.is_time_to_watch())
        mock_get.assert_called_once()

    @patch("dragonchain.transaction_processor.level_5_actions.get_last_watch_time", return_value=(int(time()) - 60))
    def test_is_time_to_watch_returns_false_if_not(self, mock_get):
        self.assertFalse(level_5_actions.is_time_to_watch())
        mock_get.assert_called_once()

    @patch("dragonchain.transaction_processor.level_5_actions.storage.does_superkey_exist")
    def test_is_backlog_calls_storage_correctly(self, mock_storage_check):
        level_5_actions.is_backlog(5)
        mock_storage_check.assert_called_once_with("BROADCAST/TO_BROADCAST/5/")

    @patch("dragonchain.transaction_processor.level_5_actions.matchmaking.update_funded_flag")
    @patch("dragonchain.transaction_processor.level_5_actions.set_funds")
    @patch("dragonchain.transaction_processor.level_5_actions.set_last_watch_time")
    def test_watch_for_funds_calls_correct_functions(self, mock_set_watch_time, mock_set_funds, mock_funded):
        level_5_actions.FUNDED = False
        level_5_actions._interchain_client.check_balance = MagicMock(return_value=500000000)
        level_5_actions._interchain_client.get_transaction_fee_estimate = MagicMock(return_value=5000)
        level_5_actions.watch_for_funds()

        level_5_actions._interchain_client.check_balance.assert_called_once()
        mock_funded.assert_called_once_with(True)
        mock_set_watch_time.assert_called_once()
        mock_set_funds.assert_called_once_with(500000000)
        self.assertTrue(level_5_actions.FUNDED)

    @patch("dragonchain.transaction_processor.level_5_actions.matchmaking.update_funded_flag")
    @patch("dragonchain.transaction_processor.level_5_actions.set_funds")
    @patch("dragonchain.transaction_processor.level_5_actions.set_last_watch_time")
    def test_watch_for_funds_does_not_update_matchmaking_if_not_necessary(self, mock_set_watch_time, mock_set_funds, mock_funded):
        level_5_actions.FUNDED = True
        level_5_actions._interchain_client.check_balance = MagicMock(return_value=500000000)
        level_5_actions._interchain_client.get_transaction_fee_estimate = MagicMock(return_value=5000)
        level_5_actions.watch_for_funds()

        level_5_actions._interchain_client.check_balance.assert_called_once()
        mock_funded.assert_not_called()
        mock_set_watch_time.assert_called_once()
        mock_set_funds.assert_called_once_with(500000000)
        self.assertTrue(level_5_actions.FUNDED)

    @patch("dragonchain.transaction_processor.level_5_actions.storage.get", return_value=b"500000000")
    def test_has_funds_for_transaction_returns_true_if_funds_exist(self, mock_get):
        level_5_actions._interchain_client.get_transaction_fee_estimate = MagicMock(return_value=5000)
        self.assertTrue(level_5_actions.has_funds_for_transactions())
        mock_get.assert_called_once()
        level_5_actions._interchain_client.get_transaction_fee_estimate.assert_called_once()

    @patch("dragonchain.transaction_processor.level_5_actions.storage.get", side_effect=exceptions.NotFound)
    def test_has_funds_for_transaction_returns_false_for_new_chain(self, mock_get):
        self.assertFalse(level_5_actions.has_funds_for_transactions())
        mock_get.assert_called_once()

    @patch("dragonchain.transaction_processor.level_5_actions.matchmaking.update_funded_flag")
    @patch("dragonchain.transaction_processor.level_5_actions.storage.get", return_value=b"50")
    def test_has_funds_for_transaction_returns_false_if_funds_dont_exist(self, mock_get, mock_fund):
        level_5_actions.FUNDED = True
        level_5_actions._interchain_client.get_transaction_fee_estimate = MagicMock(return_value=5000)

        self.assertFalse(level_5_actions.has_funds_for_transactions())
        level_5_actions._interchain_client.get_transaction_fee_estimate.assert_called_once()
        mock_fund.assert_called_once_with(False)
        self.assertFalse(level_5_actions.FUNDED)
        mock_get.assert_called_once()

    @patch("dragonchain.transaction_processor.level_5_actions.matchmaking.update_funded_flag")
    @patch("dragonchain.transaction_processor.level_5_actions.storage.get", return_value=b"50")
    def test_has_funds_for_transaction_does_not_call_matchmaking_when_not_needed(self, mock_get, mock_fund):
        level_5_actions.FUNDED = False
        level_5_actions._interchain_client.get_transaction_fee_estimate = MagicMock(return_value=5000)

        self.assertFalse(level_5_actions.has_funds_for_transactions())
        level_5_actions._interchain_client.get_transaction_fee_estimate.assert_called_once()
        mock_fund.assert_not_called()
        self.assertFalse(level_5_actions.FUNDED)
        mock_get.assert_called_once()

    @patch("dragonchain.transaction_processor.level_5_actions.party.get_address_ddss", return_value="325432")
    @patch("dragonchain.transaction_processor.level_5_actions.keys.get_public_id")
    @patch("dragonchain.transaction_processor.level_5_actions.get_pending_l4_blocks", return_value="My L4 Blocks")
    def test_create_block_creates_and_does_not_sign(self, mock_get_pending, mock_get_id, mock_registration):
        response = level_5_actions.create_l5_block("5")

        mock_get_pending.assert_called_once_with("5")
        mock_registration.assert_called_once()
        self.assertEqual(response.current_ddss, "325432")
        self.assertEqual(response.block_id, "5")
        self.assertEqual(response.prev_proof, "")
        self.assertEqual(response.l4_blocks, "My L4 Blocks")

    @patch(
        "dragonchain.transaction_processor.level_5_actions.storage.get_json_from_object",
        return_value=[{"header": {"l1_dc_id": "1", "l1_block_id": "2", "dc_id": "3", "block_id": "4"}, "proof": {"proof": "MyProof"}}],
    )
    @patch("dragonchain.transaction_processor.level_5_actions.storage.list_objects", return_value=["Key1", "Key2", "Key3"])
    def test_get_pending_l4_blocks_fetches_correctly_from_storage(self, mock_list, mock_get):
        response = level_5_actions.get_pending_l4_blocks("5")

        mock_list.assert_called_once_with("BROADCAST/TO_BROADCAST/5")
        mock_get.assert_has_calls([call("Key1"), call("Key2"), call("Key3")])
        expected_response = '{"l1_dc_id":"1","l1_block_id":"2","l4_dc_id":"3","l4_block_id":"4","l4_proof":"MyProof"}'  # noqa: B950
        self.assertEqual(response, [expected_response, expected_response, expected_response])

    @patch(
        "dragonchain.transaction_processor.level_5_actions.storage.get_json_from_object",
        return_value=[
            {"is_invalid": True, "header": {"l1_dc_id": "1", "l1_block_id": "2", "dc_id": "3", "block_id": "4"}, "proof": {"proof": "MyProof"}}
        ],
    )
    @patch("dragonchain.transaction_processor.level_5_actions.storage.list_objects", return_value=["Key1", "Key2", "Key3"])
    def test_get_pending_l4_blocks_marks_invalid_blocks(self, mock_list, mock_get):
        response = level_5_actions.get_pending_l4_blocks("5")

        mock_list.assert_called_once_with("BROADCAST/TO_BROADCAST/5")
        mock_get.assert_has_calls([call("Key1"), call("Key2"), call("Key3")])
        expected_response = '{"l1_dc_id":"1","l1_block_id":"2","l4_dc_id":"3","l4_block_id":"4","l4_proof":"MyProof","is_invalid":true}'  # noqa: B950
        self.assertEqual(response, [expected_response, expected_response, expected_response])

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
from unittest.mock import patch, MagicMock, AsyncMock, call, ANY

from dragonchain import test_env  # noqa: F401
from dragonchain.broadcast_processor import broadcast_functions
from dragonchain import exceptions


class BroadcastFunctionTests(unittest.IsolatedAsyncioTestCase):
    def test_state_key_returns_correct_key(self):
        self.assertEqual(broadcast_functions.state_key("id"), "broadcast:block:id:state")

    def test_verifications_key_returns_correct_key(self):
        self.assertEqual(broadcast_functions.verifications_key("id", 2), "broadcast:block:id:l2")

    def test_error_key_returns_correct_key(self):
        self.assertEqual(broadcast_functions.storage_error_key("id"), "broadcast:block:id:errors")

    @patch("dragonchain.broadcast_processor.broadcast_functions.storage_error_key")
    def test_storage_error_no_op_when_low_level(self, patch_error_key):
        broadcast_functions.increment_storage_error_sync("blah", 2)
        broadcast_functions.increment_storage_error_sync("blah", 1)
        patch_error_key.assert_not_called()

    @patch("dragonchain.broadcast_processor.broadcast_functions.storage_error_key", return_value="key")
    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.get_sync", return_value=b"2")
    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.set_sync")
    def test_storage_error_increments_redis_value_correctly(self, set_sync, get_sync, patch_error_key):
        broadcast_functions.increment_storage_error_sync("blah", 3)
        get_sync.assert_called_once_with("key", decode=False)
        set_sync.assert_called_once_with("key", "3")

    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.pipeline_sync")
    @patch("dragonchain.broadcast_processor.broadcast_functions.storage_error_key", return_value="error_key")
    @patch("dragonchain.broadcast_processor.broadcast_functions.verifications_key", return_value="verifications_key")
    @patch("dragonchain.broadcast_processor.broadcast_functions.state_key", return_value="state_key")
    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.get_sync", return_value="99999")
    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.smembers_sync", return_value={"abc", "def"})
    @patch("dragonchain.broadcast_processor.broadcast_functions.storage.list_objects", return_value=["BLOCK/blah-l2-abc"])
    def test_storage_error_rolls_back_state_correctly_when_needed(
        self, list_objects, smembers_sync, get_sync, state_key, verifications_key, error_key, mock_pipeline
    ):
        fake_pipeline = MagicMock()
        mock_pipeline.return_value = fake_pipeline
        broadcast_functions.increment_storage_error_sync("blah", 3)
        mock_pipeline.assert_called_once()
        fake_pipeline.srem.assert_called_once_with("verifications_key", "def")
        fake_pipeline.delete.assert_called_once_with("error_key")
        fake_pipeline.set.assert_called_once_with("state_key", "2")
        fake_pipeline.execute.assert_called_once()

    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.z_range_by_score_async", return_value="dummy")
    @patch("dragonchain.broadcast_processor.broadcast_functions.time.time", return_value=123)
    async def test_get_for_process_async(self, mock_time, mock_zrange):
        self.assertEqual(await broadcast_functions.get_blocks_to_process_for_broadcast_async(), "dummy")
        mock_time.assert_called_once()
        mock_zrange.assert_awaited_once_with("broadcast:in-flight", 0, 123, withscores=True, offset=0, count=1000)

    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.get_async", return_value="3")
    @patch("dragonchain.broadcast_processor.broadcast_functions.state_key", return_value="key")
    async def test_get_block_level_async(self, mock_key, mock_get):
        self.assertEqual(await broadcast_functions.get_current_block_level_async("blah"), 3)
        mock_get.assert_awaited_once_with("key", decode=False)

    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.get_sync", return_value=b"3")
    @patch("dragonchain.broadcast_processor.broadcast_functions.state_key", return_value="key")
    def test_get_block_level_sync(self, mock_key, mock_get):
        self.assertEqual(broadcast_functions.get_current_block_level_sync("blah"), 3)
        mock_get.assert_called_once_with("key", decode=False)

    @patch("dragonchain.broadcast_processor.broadcast_functions.get_current_block_level_sync", return_value=3)
    def test_block_accepting_from_level(self, mock_get_block_level):
        self.assertTrue(broadcast_functions.is_block_accepting_verifications_from_level("blah", 3))
        mock_get_block_level.assert_called_once_with("blah")
        self.assertFalse(broadcast_functions.is_block_accepting_verifications_from_level("blah", 4))

    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.set_async")
    @patch("dragonchain.broadcast_processor.broadcast_functions.state_key", return_value="key")
    async def test_set_block_level_async_calls_redis_with_correct_params(self, mock_key, mock_set):
        await broadcast_functions.set_current_block_level_async("blah", 3)
        mock_set.assert_awaited_once_with("key", "3")

    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.set_sync")
    @patch("dragonchain.broadcast_processor.broadcast_functions.state_key", return_value="key")
    def test_set_block_level_sync_calls_redis_with_correct_params(self, mock_key, mock_set):
        broadcast_functions.set_current_block_level_sync("blah", 3)
        mock_set.assert_called_once_with("key", "3")

    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.zadd_async")
    async def test_schedule_block_async_calls_redis_with_correct_params(self, mock_zadd):
        await broadcast_functions.schedule_block_for_broadcast_async("id", 123)
        mock_zadd.assert_awaited_once_with("broadcast:in-flight", 123, "id")

    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.zadd_sync")
    def test_schedule_block_sync_calls_redis_with_correct_params(self, mock_zadd):
        broadcast_functions.schedule_block_for_broadcast_sync("id", 123)
        mock_zadd.assert_called_once_with("broadcast:in-flight", {"id": 123})

    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.pipeline_sync")
    @patch("dragonchain.broadcast_processor.broadcast_functions.verifications_key", return_value="verification_key")
    def test_get_all_verifications_sync(self, mock_verification_key, mock_pipeline):
        fake_pipeline = MagicMock()
        fake_pipeline.execute.return_value = [{b"l2chain1", b"l2chain2"}, {b"l3chain"}, {b"l4chain"}, set()]
        mock_pipeline.return_value = fake_pipeline

        result = broadcast_functions.get_all_verifications_for_block_sync("id")

        # Check that mocks were called as expected
        mock_pipeline.assert_called_once()
        smembers_calls = [call("verification_key"), call("verification_key"), call("verification_key"), call("verification_key")]
        fake_pipeline.smembers.assert_has_calls(smembers_calls)
        fake_pipeline.execute.assert_called_once()
        verification_key_calls = [call("id", 2), call("id", 3), call("id", 4), call("id", 5)]
        mock_verification_key.assert_has_calls(verification_key_calls)

        # Check actual result
        self.assertEqual(result, [{"l2chain1", "l2chain2"}, {"l3chain"}, {"l4chain"}, set()])

    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.smembers_sync", return_value={b"thing"})
    @patch("dragonchain.broadcast_processor.broadcast_functions.verifications_key", return_value="key")
    def test_get_verifications_sync(self, mock_key, mock_smembers):
        self.assertEqual(broadcast_functions.get_receieved_verifications_for_block_and_level_sync("id", 2), {b"thing"})
        mock_smembers.assert_called_once_with("key")

    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.smembers_async", return_value={"thing"})
    @patch("dragonchain.broadcast_processor.broadcast_functions.verifications_key", return_value="key")
    async def test_get_verifications_async(self, mock_key, mock_smembers):
        self.assertEqual(await broadcast_functions.get_receieved_verifications_for_block_and_level_async("id", 2), {"thing"})
        mock_smembers.assert_awaited_once_with("key")

    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.pipeline_sync")
    @patch("dragonchain.broadcast_processor.broadcast_functions.state_key", return_value="state_key")
    @patch("dragonchain.broadcast_processor.broadcast_functions.verifications_key", return_value="verification_key")
    @patch("dragonchain.broadcast_processor.broadcast_functions.storage_error_key", return_value="storage_error_key")
    def test_remove_block_sync_calls_redis_with_correct_deletes(self, mock_error_key, mock_verification_key, mock_state_key, mock_pipeline):
        fake_pipeline = MagicMock()
        mock_pipeline.return_value = fake_pipeline
        broadcast_functions.remove_block_from_broadcast_system_sync("id")
        mock_pipeline.assert_called_once()
        fake_pipeline.zrem.assert_called_once_with("broadcast:in-flight", "id")
        fake_pipeline.hdel.assert_called_once_with("broadcast:claimcheck", "id")
        delete_calls = [
            call("state_key"),
            call("storage_error_key"),
            call("verification_key"),
            call("verification_key"),
            call("verification_key"),
            call("verification_key"),
        ]
        fake_pipeline.delete.assert_has_calls(delete_calls)
        fake_pipeline.execute.assert_called_once()
        mock_state_key.assert_called_once_with("id")
        verification_key_calls = [call("id", 2), call("id", 3), call("id", 4), call("id", 5)]
        mock_verification_key.assert_has_calls(verification_key_calls)

    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.multi_exec_async")
    @patch("dragonchain.broadcast_processor.broadcast_functions.state_key", return_value="state_key")
    @patch("dragonchain.broadcast_processor.broadcast_functions.verifications_key", return_value="verification_key")
    @patch("dragonchain.broadcast_processor.broadcast_functions.storage_error_key", return_value="storage_error_key")
    async def test_remove_block_async_calls_redis_with_correct_deletes(self, mock_error_key, mock_verification_key, mock_state_key, mock_multi_exec):
        fake_pipeline = MagicMock(execute=AsyncMock())
        mock_multi_exec.return_value = fake_pipeline
        await broadcast_functions.remove_block_from_broadcast_system_async("id")
        mock_multi_exec.assert_awaited_once()
        fake_pipeline.zrem.assert_called_once_with("broadcast:in-flight", "id")
        fake_pipeline.hdel.assert_called_once_with("broadcast:claimcheck", "id")
        delete_calls = [
            call("state_key"),
            call("storage_error_key"),
            call("verification_key"),
            call("verification_key"),
            call("verification_key"),
            call("verification_key"),
        ]
        fake_pipeline.delete.assert_has_calls(delete_calls)
        fake_pipeline.execute.assert_awaited_once()
        mock_state_key.assert_called_once_with("id")
        verification_key_calls = [call("id", 2), call("id", 3), call("id", 4), call("id", 5)]
        mock_verification_key.assert_has_calls(verification_key_calls)

    @patch("dragonchain.broadcast_processor.broadcast_functions.dragonnet_config.DRAGONNET_CONFIG", {})
    @patch("dragonchain.broadcast_processor.broadcast_functions.get_current_block_level_sync", return_value=3)
    def test_set_record_for_block_sync_raises_when_not_accepting_level(self, mock_get_block_level):
        self.assertRaises(
            exceptions.NotAcceptingVerifications, broadcast_functions.set_receieved_verification_for_block_from_chain_sync, "block_id", 2, "chain_id"
        )

    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.pipeline_sync")
    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.sadd_sync")
    @patch("dragonchain.broadcast_processor.broadcast_functions.dragonnet_config.DRAGONNET_CONFIG", {"l2": {"nodesRequired": 3}})
    @patch("dragonchain.broadcast_processor.broadcast_functions.verifications_key", return_value="key")
    @patch("dragonchain.broadcast_processor.broadcast_functions.get_current_block_level_sync", return_value=2)
    def test_set_record_for_block_sync_calls_redis_with_correct_params(self, mock_get_block_level, mock_key, mock_sadd, mock_pipeline):
        fake_pipeline = MagicMock()
        fake_pipeline.execute.return_value = [1, 2]
        mock_pipeline.return_value = fake_pipeline
        broadcast_functions.set_receieved_verification_for_block_from_chain_sync("block_id", 2, "chain_id")
        mock_pipeline.assert_called_once()
        fake_pipeline.sadd.assert_called_once_with("key", "chain_id")
        fake_pipeline.scard.assert_called_once_with("key")
        fake_pipeline.execute.assert_called_once()

    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.pipeline_sync")
    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.sadd_sync")
    @patch("dragonchain.broadcast_processor.broadcast_functions.dragonnet_config.DRAGONNET_CONFIG", {"l3": {"nodesRequired": 3}})
    @patch("dragonchain.broadcast_processor.broadcast_functions.set_current_block_level_sync")
    @patch("dragonchain.broadcast_processor.broadcast_functions.schedule_block_for_broadcast_sync")
    @patch("dragonchain.broadcast_processor.broadcast_functions.verifications_key", return_value="key")
    @patch("dragonchain.broadcast_processor.broadcast_functions.get_current_block_level_sync", return_value=3)
    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.delete_sync")
    def test_set_record_for_block_sync_promotes_when_needed_met(
        self, mock_delete_sync, mock_get_block_level, mock_key, mock_schedule, mock_set_block, mock_sadd, mock_pipeline
    ):
        fake_pipeline = MagicMock()
        fake_pipeline.execute.return_value = [1, 3]
        mock_pipeline.return_value = fake_pipeline
        broadcast_functions.set_receieved_verification_for_block_from_chain_sync("block_id", 3, "chain_id")
        mock_set_block.assert_called_once_with("block_id", 4)
        mock_schedule.assert_called_once_with("block_id")

    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.pipeline_sync")
    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.sadd_sync")
    @patch("dragonchain.broadcast_processor.broadcast_functions.dragonnet_config.DRAGONNET_CONFIG", {"l5": {"nodesRequired": 3}})
    @patch("dragonchain.broadcast_processor.broadcast_functions.remove_block_from_broadcast_system_sync")
    @patch("dragonchain.broadcast_processor.broadcast_functions.verifications_key", return_value="key")
    @patch("dragonchain.broadcast_processor.broadcast_functions.get_current_block_level_sync", return_value=5)
    def test_set_record_for_block_sync_calls_remove_when_required_met_and_level_5(
        self, mock_get_block_level, mock_key, mock_remove, mock_sadd, mock_pipeline
    ):
        fake_pipeline = MagicMock()
        fake_pipeline.execute.return_value = [1, 3]
        mock_pipeline.return_value = fake_pipeline
        broadcast_functions.set_receieved_verification_for_block_from_chain_sync("block_id", 5, "chain_id")
        mock_remove.assert_called_once_with("block_id")

    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.smembers_async", return_value={"thing"})
    async def test_get_notification_verifications_for_broadcast_async(self, mock_smembers):
        await broadcast_functions.get_notification_verifications_for_broadcast_async()
        mock_smembers.assert_awaited_once_with("broadcast:notifications")

    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.srem_async", return_value=1)
    async def test_remove_notification_verification_for_broadcast_async(self, mock_srem):
        await broadcast_functions.remove_notification_verification_for_broadcast_async("banana")
        mock_srem.assert_awaited_once_with("broadcast:notifications", "banana")

    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.sadd_sync", return_value=1)
    def test_schedule_notification_for_broadcast_sync(self, mock_sadd):
        broadcast_functions.schedule_notification_for_broadcast_sync("banana")
        mock_sadd.assert_called_once_with("broadcast:notifications", "banana")

    def test_verification_storage_location(self):
        result = broadcast_functions.verification_storage_location("l1_block_id", 2, "chain_id")
        self.assertEqual(result, "BLOCK/l1_block_id-l2-chain_id")

    @patch("dragonchain.broadcast_processor.broadcast_functions.remove_block_from_broadcast_system_async")
    @patch("dragonchain.broadcast_processor.broadcast_functions.storage.put_object_as_json")
    async def test_save_unfinished_claim_writes_to_storage(self, mock_put, mock_remove):
        await broadcast_functions.save_unfinished_claim("123")
        mock_put.assert_called_once_with("BROADCASTS/UNFINISHED/123", ANY)

    @patch("dragonchain.broadcast_processor.broadcast_functions.remove_block_from_broadcast_system_async")
    @patch("dragonchain.broadcast_processor.broadcast_functions.storage")
    async def test_save_unfinished_claim_removes_claim_from_system(self, mock_storage, mock_remove):
        await broadcast_functions.save_unfinished_claim("123")
        mock_remove.assert_awaited_once_with("123")

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

import importlib
import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from dragonchain import test_env  # noqa: F401
from dragonchain.broadcast_processor import broadcast_processor
from dragonchain import exceptions


class BroadcastProcessorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        importlib.reload(broadcast_processor)
        broadcast_processor.BROADCAST = "true"
        broadcast_processor.LEVEL = "1"
        broadcast_processor._requirements = {
            "l2": {"nodesRequired": 2},
            "l3": {"nodesRequired": 3},
            "l4": {"nodesRequired": 4},
            "l5": {"nodesRequired": 5},
        }

    def test_setup_raises_error_when_not_level_1(self):
        broadcast_processor.LEVEL = "2"
        self.assertRaises(RuntimeError, broadcast_processor.setup)

    def test_setup_raises_error_when_not_broadcasting(self):
        broadcast_processor.BROADCAST = "false"
        self.assertRaises(RuntimeError, broadcast_processor.setup)

    @patch("dragonchain.broadcast_processor.broadcast_processor.dragonnet_config.DRAGONNET_CONFIG", 4)
    def test_setup_sets_module_vars_correctly(self):
        broadcast_processor.setup()
        self.assertEqual(broadcast_processor._requirements, 4)

    def test_needed_verifications_returns_correct_value_from_requirements(self):
        self.assertEqual(broadcast_processor.needed_verifications(2), 2)
        self.assertEqual(broadcast_processor.needed_verifications(3), 3)
        self.assertEqual(broadcast_processor.needed_verifications(4), 4)
        self.assertEqual(broadcast_processor.needed_verifications(5), 5)

    def test_chain_id_from_matchmaking_claim_returns_correct(self):
        fake_claim = {"validations": {"l2": {"test2": {}}, "l3": {"test3": {}}, "l4": {"test4": {}}, "l5": {"test5": {}}}}
        self.assertEqual(broadcast_processor.chain_id_set_from_matchmaking_claim(fake_claim, 2), {"test2"})
        self.assertEqual(broadcast_processor.chain_id_set_from_matchmaking_claim(fake_claim, 3), {"test3"})
        self.assertEqual(broadcast_processor.chain_id_set_from_matchmaking_claim(fake_claim, 4), {"test4"})
        self.assertEqual(broadcast_processor.chain_id_set_from_matchmaking_claim(fake_claim, 5), {"test5"})

    def test_get_level_from_storage_location_returns_level_string(self):
        level = broadcast_processor.get_level_from_storage_location("/BLOCK/something-l3-asdfsdf")
        self.assertEqual(level, "3")

    def test_get_level_from_storage_location_returns_none_when_fails(self):
        self.assertIsNone(broadcast_processor.get_level_from_storage_location("/BLOCK/something-apples-asdfsdf"))

    def test_notification_urls_returns_set(self):
        urls = broadcast_processor.get_notification_urls("banana")
        self.assertEqual(type(urls), set)

    @patch.dict("dragonchain.broadcast_processor.broadcast_processor.VERIFICATION_NOTIFICATION", {"all": ["url1"]})
    def test_notification_urls_returns_values_from_env(self):
        urls = broadcast_processor.get_notification_urls("all")
        self.assertEqual(urls, {"url1"})

    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.matchmaking.get_registration",
        return_value={"network": "bitcoin mainnet", "broadcastInterval": 1.23},
    )
    def test_set_l5_wait_time_success(self, mock_get_rego):
        self.assertEqual(broadcast_processor.set_l5_wait_time("chainid"), 15228)  # (600 * 6 * 3) + ((1.23 * 60) *60)
        mock_get_rego.assert_called_once_with("chainid")

    @patch("dragonchain.broadcast_processor.broadcast_processor.matchmaking.get_registration", return_value={"fruit": "banana"})
    def test_set_l5_wait_time_throws_exception(self, mock_get_rego):
        self.assertEqual(broadcast_processor.set_l5_wait_time("chainid"), 43200)  # hardcoded fallback value
        mock_get_rego.assert_called_once_with("chainid")

    @patch.dict("dragonchain.broadcast_processor.broadcast_processor._l5_wait_times", {"banana": 123})
    @patch("dragonchain.broadcast_processor.broadcast_processor.matchmaking.get_registration")
    def test_get_l5_wait_time_is_cached(self, mock_get_rego):
        self.assertEqual(broadcast_processor.get_l5_wait_time("banana"), 123)
        mock_get_rego.assert_not_called()

    @patch.dict("dragonchain.broadcast_processor.broadcast_processor._l5_wait_times", {})
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.matchmaking.get_registration",
        return_value={"network": "bitcoin mainnet", "broadcastInterval": 1.23},
    )
    def test_get_l5_wait_time_not_cached(self, mock_get_rego):
        self.assertEqual(broadcast_processor.get_l5_wait_time("chainid"), 15228)
        mock_get_rego.assert_called_once_with("chainid")

    @patch("dragonchain.broadcast_processor.broadcast_processor.block_dao.get_broadcast_dto")
    def test_broadcast_futures_gets_broadcast_dto_for_block_id(self, patch_get_broadcast):
        broadcast_processor.make_broadcast_futures(None, "id", 3, set())
        patch_get_broadcast.assert_called_once_with(3, "id")

    @patch("dragonchain.broadcast_processor.broadcast_processor.block_dao.get_broadcast_dto", return_value="dto")
    @patch("dragonchain.broadcast_processor.broadcast_processor.asyncio.create_task", return_value="task")
    @patch("dragonchain.broadcast_processor.broadcast_processor.matchmaking.get_dragonchain_address", return_value="addr")
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.authorization.generate_authenticated_request",
        return_value=({"header": "thing"}, b"some data"),
    )
    def test_broadcast_futures_returns_set_of_futures_from_session_posts(
        self, mock_gen_request, mock_get_address, mock_create_task, patch_get_broadcast
    ):
        fake_session = MagicMock()
        fake_session.post = MagicMock(return_value="session_request")
        self.assertEqual(broadcast_processor.make_broadcast_futures(fake_session, "block_id", 2, {"chain_id"}), {"task"})
        mock_get_address.assert_called_once_with("chain_id")
        mock_create_task.assert_called_once_with("session_request")
        mock_gen_request.assert_called_once_with("POST", "chain_id", "/v1/enqueue", "dto")
        fake_session.post.assert_called_once_with(
            url="addr/v1/enqueue",
            data=b"some data",
            headers={"header": "thing", "deadline": str(broadcast_processor.BROADCAST_RECEIPT_WAIT_TIME)},
            timeout=broadcast_processor.HTTP_REQUEST_TIMEOUT,
        )

    @patch("dragonchain.broadcast_processor.broadcast_processor.asyncio.create_task", return_value="task")
    @patch("dragonchain.broadcast_processor.broadcast_processor.matchmaking.get_dragonchain_address", return_value="addr")
    @patch("dragonchain.broadcast_processor.broadcast_processor.block_dao.get_broadcast_dto", return_value="dto")
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.authorization.generate_authenticated_request",
        return_value=({"header": "thing"}, b"some data"),
    )
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.matchmaking.get_registration",
        return_value={"network": "bitcoin mainnet", "broadcastInterval": 1.23},
    )
    def test_broadcast_futures_sets_deadline_header_for_l5(self, mock_get_rego, mock_gen_request, mock_get_address, mock_create_task, mock_dto):
        fake_session = MagicMock()
        fake_session.post = MagicMock(return_value="session_request")
        broadcast_processor.make_broadcast_futures(fake_session, "block_id", 5, {"chain_id"})
        fake_session.post.assert_called_once_with(
            url="addr/v1/enqueue",
            data=b"some data",
            headers={"header": "thing", "deadline": "15228"},
            timeout=broadcast_processor.HTTP_REQUEST_TIMEOUT,
        )

    @patch("dragonchain.broadcast_processor.broadcast_processor.block_dao.get_broadcast_dto", return_value="dto")
    @patch("dragonchain.broadcast_processor.broadcast_processor.matchmaking.get_dragonchain_address", return_value="addr")
    @patch("dragonchain.broadcast_processor.broadcast_processor.authorization.generate_authenticated_request", side_effect=Exception)
    def test_broadcast_futures_doesnt_return_future_for_exception_with_a_chain(self, mock_gen_req, mock_get_address, patch_get_broadcast):
        fake_session = MagicMock()
        fake_session.post = MagicMock(return_value="session_request")
        self.assertEqual(broadcast_processor.make_broadcast_futures(fake_session, "block_id", 2, {"chain_id"}), set())

    @patch("dragonchain.broadcast_processor.broadcast_processor.block_dao.get_broadcast_dto", side_effect=exceptions.NotEnoughVerifications)
    @patch("dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.increment_storage_error_sync")
    def test_broadcast_futures_returns_none_on_get_broadcast_dto_failure(self, mock_increment_error, patch_get_broadcast):
        self.assertIsNone(broadcast_processor.make_broadcast_futures(None, "block_id", 2, {"chain_id"}))
        mock_increment_error.assert_called_once_with("block_id", 2)

    @patch("dragonchain.broadcast_processor.broadcast_processor.asyncio.gather", return_value=asyncio.Future())
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_blocks_to_process_for_broadcast_async", return_value=[],
    )
    async def test_process_blocks_gets_blocks_for_broadcast(self, mock_get_blocks, mock_gather):
        mock_gather.return_value.set_result(None)
        await broadcast_processor.process_blocks_for_broadcast(None)
        mock_get_blocks.assert_called_once()

    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.matchmaking.get_or_create_claim_check",
        return_value={"metadata": {"dcId": "banana-dc-id"}},
    )
    @patch("dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.schedule_block_for_broadcast_async")
    @patch("dragonchain.broadcast_processor.broadcast_processor.make_broadcast_futures")
    @patch("dragonchain.broadcast_processor.broadcast_processor.chain_id_set_from_matchmaking_claim")
    @patch("dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_current_block_level_async", return_value=2)
    @patch("dragonchain.broadcast_processor.broadcast_processor.asyncio.gather", return_value=asyncio.Future())
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_blocks_to_process_for_broadcast_async",
        return_value=[("block_id", 0)],
    )
    async def test_process_blocks_calls_matchmaking_for_claims(
        self, mock_get_blocks, mock_gather, mock_get_block_level, mock_chain_id_set, mock_get_futures, mock_schedule_broadcast, mock_claim
    ):
        mock_gather.return_value.set_result(None)
        await broadcast_processor.process_blocks_for_broadcast(None)
        mock_claim.assert_called_once_with("block_id", broadcast_processor._requirements)
        mock_chain_id_set.assert_called_once_with({"metadata": {"dcId": "banana-dc-id"}}, 2)

    @patch("dragonchain.broadcast_processor.broadcast_processor.matchmaking.get_or_create_claim_check", side_effect=exceptions.InsufficientFunds)
    @patch("dragonchain.broadcast_processor.broadcast_processor.asyncio.sleep")
    @patch("dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_current_block_level_async", return_value=None)
    @patch("dragonchain.broadcast_processor.broadcast_processor.asyncio.gather", return_value=asyncio.Future())
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_blocks_to_process_for_broadcast_async",
        return_value=[("block_id", 0)],
    )
    async def test_process_blocks_sleeps_with_insufficient_funds(self, mock_get_blocks, mock_gather, mock_get_block_level, mock_sleep, mock_claim):
        mock_gather.return_value.set_result(None)
        await broadcast_processor.process_blocks_for_broadcast(None)
        mock_sleep.assert_called_once_with(1800)

    @patch("dragonchain.broadcast_processor.broadcast_processor.matchmaking.get_or_create_claim_check")
    @patch("dragonchain.broadcast_processor.broadcast_processor.time.time", return_value=123)
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_receieved_verifications_for_block_and_level_async",
        return_value=None,
    )
    @patch("dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.schedule_block_for_broadcast_async")
    @patch("dragonchain.broadcast_processor.broadcast_processor.make_broadcast_futures")
    @patch("dragonchain.broadcast_processor.broadcast_processor.chain_id_set_from_matchmaking_claim", return_value={"chain_id"})
    @patch("dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_current_block_level_async", return_value=2)
    @patch("dragonchain.broadcast_processor.broadcast_processor.asyncio.gather", return_value=asyncio.Future())
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_blocks_to_process_for_broadcast_async",
        return_value=[("block_id", 0)],
    )
    async def test_process_blocks_fires_requests_and_reschedules_for_new_block(
        self,
        mock_get_blocks,
        mock_gather,
        mock_get_block_level,
        mock_chain_id_set,
        mock_get_futures,
        mock_schedule_broadcast,
        mock_get_verifications,
        mock_time,
        mock_claim,
    ):
        mock_gather.return_value.set_result(None)
        await broadcast_processor.process_blocks_for_broadcast(None)
        mock_get_futures.assert_called_once_with(None, "block_id", 2, {"chain_id"})
        mock_schedule_broadcast.assert_called_once_with("block_id", 123 + broadcast_processor.BROADCAST_RECEIPT_WAIT_TIME)
        mock_gather.assert_called_once_with(return_exceptions=True)
        mock_get_verifications.assert_not_called()

    @patch("dragonchain.broadcast_processor.broadcast_processor.matchmaking.get_or_create_claim_check")
    @patch("dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.schedule_block_for_broadcast_async")
    @patch("dragonchain.broadcast_processor.broadcast_processor.make_broadcast_futures", return_value=None)
    @patch("dragonchain.broadcast_processor.broadcast_processor.chain_id_set_from_matchmaking_claim", return_value={"chain_id"})
    @patch("dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_current_block_level_async", return_value=2)
    @patch("dragonchain.broadcast_processor.broadcast_processor.asyncio.gather", return_value=asyncio.Future())
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_blocks_to_process_for_broadcast_async",
        return_value=[("block_id", 0)],
    )
    async def test_process_blocks_doesnt_reschedule_new_block_which_failed_had_no_futures(
        self, mock_get_blocks, mock_gather, mock_get_block_level, mock_chain_id_set, mock_get_futures, mock_schedule_broadcast, mock_claim
    ):
        mock_gather.return_value.set_result(None)
        await broadcast_processor.process_blocks_for_broadcast(None)
        mock_get_futures.assert_called_once()
        mock_schedule_broadcast.assert_not_called()

    @patch("dragonchain.broadcast_processor.broadcast_processor.matchmaking.get_or_create_claim_check")
    @patch("dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.set_current_block_level_async")
    @patch("dragonchain.broadcast_processor.broadcast_processor.needed_verifications", return_value=0)
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_receieved_verifications_for_block_and_level_async",
        return_value={"verification"},
    )
    @patch("dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.schedule_block_for_broadcast_async")
    @patch("dragonchain.broadcast_processor.broadcast_processor.make_broadcast_futures")
    @patch("dragonchain.broadcast_processor.broadcast_processor.chain_id_set_from_matchmaking_claim", return_value={"chain_id"})
    @patch("dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_current_block_level_async", return_value=2)
    @patch("dragonchain.broadcast_processor.broadcast_processor.asyncio.gather", return_value=asyncio.Future())
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_blocks_to_process_for_broadcast_async",
        return_value=[("block_id", 1)],
    )
    async def test_process_blocks_promotes_block_with_enough_verifications(
        self,
        mock_get_blocks,
        mock_gather,
        mock_get_block_level,
        mock_chain_id_set,
        mock_get_futures,
        mock_schedule_broadcast,
        mock_get_verifications,
        mock_needed_verifications,
        mock_set_block_level,
        mock_claim_check,
    ):
        mock_gather.return_value.set_result(None)
        await broadcast_processor.process_blocks_for_broadcast(None)
        mock_set_block_level.assert_called_once_with("block_id", 3)
        mock_schedule_broadcast.assert_called_once_with("block_id")

    @patch("dragonchain.broadcast_processor.broadcast_processor.matchmaking.get_or_create_claim_check")
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.remove_block_from_broadcast_system_async",
        return_value=asyncio.Future(),
    )
    @patch("dragonchain.broadcast_processor.broadcast_processor.needed_verifications", return_value=0)
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_receieved_verifications_for_block_and_level_async",
        return_value={"verification"},
    )
    @patch("dragonchain.broadcast_processor.broadcast_processor.make_broadcast_futures")
    @patch("dragonchain.broadcast_processor.broadcast_processor.chain_id_set_from_matchmaking_claim", return_value={"chain_id"})
    @patch("dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_current_block_level_async", return_value=5)
    @patch("dragonchain.broadcast_processor.broadcast_processor.asyncio.gather", return_value=asyncio.Future())
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_blocks_to_process_for_broadcast_async",
        return_value=[("block_id", 1)],
    )
    async def test_process_blocks_removes_l5_block_with_enough_verifications(
        self,
        mock_get_blocks,
        mock_gather,
        mock_get_block_level,
        mock_chain_id_set,
        mock_get_futures,
        mock_get_verifications,
        mock_needed_verifications,
        mock_remove_block,
        mock_claim_check,
    ):
        mock_gather.return_value.set_result(None)
        mock_remove_block.return_value.set_result(None)
        await broadcast_processor.process_blocks_for_broadcast(None)
        mock_remove_block.assert_called_once_with("block_id")

    @patch("dragonchain.broadcast_processor.broadcast_processor.matchmaking.get_or_create_claim_check")
    @patch("dragonchain.broadcast_processor.broadcast_processor.matchmaking.overwrite_no_response_node")
    @patch("dragonchain.broadcast_processor.broadcast_processor.needed_verifications", return_value=3)
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_receieved_verifications_for_block_and_level_async",
        return_value={"verification"},
    )
    @patch("dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.schedule_block_for_broadcast_async")
    @patch("dragonchain.broadcast_processor.broadcast_processor.make_broadcast_futures")
    @patch("dragonchain.broadcast_processor.broadcast_processor.chain_id_set_from_matchmaking_claim", return_value={"chain_id"})
    @patch("dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_current_block_level_async", return_value=2)
    @patch("dragonchain.broadcast_processor.broadcast_processor.asyncio.gather", return_value=asyncio.Future())
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_blocks_to_process_for_broadcast_async",
        return_value=[("block_id", 1)],
    )
    async def test_process_blocks_updates_matchmaking_claim_for_new_chain_verification(
        self,
        mock_get_blocks,
        mock_gather,
        mock_get_block_level,
        mock_chain_id_set,
        mock_get_futures,
        mock_schedule_broadcast,
        mock_get_verifications,
        mock_needed_verifications,
        mock_no_response_node,
        mock_claim_check,
    ):
        mock_gather.return_value.set_result(None)
        await broadcast_processor.process_blocks_for_broadcast(None)
        mock_no_response_node.assert_called_once_with("block_id", 2, "chain_id")

    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.matchmaking.get_or_create_claim_check",
        return_value={"metadata": {"dcId": "banana-dc-id"}},
    )
    @patch("dragonchain.broadcast_processor.broadcast_processor.matchmaking.overwrite_no_response_node", return_value={"verification"})
    @patch("dragonchain.broadcast_processor.broadcast_processor.time.time", return_value=123)
    @patch("dragonchain.broadcast_processor.broadcast_processor.needed_verifications", return_value=3)
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_receieved_verifications_for_block_and_level_async",
        return_value={"verification"},
    )
    @patch("dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.schedule_block_for_broadcast_async")
    @patch("dragonchain.broadcast_processor.broadcast_processor.make_broadcast_futures")
    @patch("dragonchain.broadcast_processor.broadcast_processor.chain_id_set_from_matchmaking_claim", return_value={"chain_id"})
    @patch("dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_current_block_level_async", return_value=2)
    @patch("dragonchain.broadcast_processor.broadcast_processor.asyncio.gather", return_value=asyncio.Future())
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_blocks_to_process_for_broadcast_async",
        return_value=[("block_id", 1)],
    )
    async def test_process_blocks_makes_broadcast_and_reschedules_block_when_sending_new_requests(
        self,
        mock_get_blocks,
        mock_gather,
        mock_get_block_level,
        mock_chain_id_set,
        mock_get_futures,
        mock_schedule_broadcast,
        mock_get_verifications,
        mock_needed_verifications,
        mock_time,
        mock_no_response_node,
        mock_claim_check,
    ):
        mock_gather.return_value.set_result(None)
        await broadcast_processor.process_blocks_for_broadcast(None)
        mock_get_futures.assert_called_once_with(None, "block_id", 2, {"chain_id"})
        mock_schedule_broadcast.assert_called_once_with("block_id", 123 + broadcast_processor.BROADCAST_RECEIPT_WAIT_TIME)
        mock_gather.assert_called_once_with(return_exceptions=True)

    @patch("dragonchain.broadcast_processor.broadcast_processor.matchmaking.get_or_create_claim_check")
    @patch("dragonchain.broadcast_processor.broadcast_processor.matchmaking.overwrite_no_response_node", return_value={"verification"})
    @patch("dragonchain.broadcast_processor.broadcast_processor.needed_verifications", return_value=3)
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_receieved_verifications_for_block_and_level_async",
        return_value={"verification"},
    )
    @patch("dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.schedule_block_for_broadcast_async")
    @patch("dragonchain.broadcast_processor.broadcast_processor.make_broadcast_futures", return_value=None)
    @patch("dragonchain.broadcast_processor.broadcast_processor.chain_id_set_from_matchmaking_claim", return_value={"chain_id"})
    @patch("dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_current_block_level_async", return_value=2)
    @patch("dragonchain.broadcast_processor.broadcast_processor.asyncio.gather", return_value=asyncio.Future())
    @patch(
        "dragonchain.broadcast_processor.broadcast_processor.broadcast_functions.get_blocks_to_process_for_broadcast_async",
        return_value=[("block_id", 1)],
    )
    async def test_process_blocks_doesnt_reschedule_existing_block_which_failed_had_no_futures(
        self,
        mock_get_blocks,
        mock_gather,
        mock_get_block_level,
        mock_chain_id_set,
        mock_get_futures,
        mock_schedule_broadcast,
        mock_get_verifications,
        mock_needed_verifications,
        mock_no_response_node,
        mock_claim_check,
    ):
        mock_gather.return_value.set_result(None)
        await broadcast_processor.process_blocks_for_broadcast(None)
        mock_get_futures.assert_called_once()
        mock_schedule_broadcast.assert_not_called()

    @patch(
        "dragonchain.broadcast_processor.broadcast_functions.get_notification_verifications_for_broadcast_async",
        return_value={"BLOCK/banana-l2-whatever"},
    )
    @patch("dragonchain.broadcast_processor.broadcast_processor.sign", return_value="my-signature")
    @patch("dragonchain.broadcast_processor.broadcast_processor.storage.get", return_value=b"location-object-bytes")
    @patch("dragonchain.broadcast_processor.broadcast_processor.keys.get_public_id", return_value="my-public-id")
    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.srem_async", return_value="OK")
    async def test_process_verification_notification_calls_configured_url(
        self, srem_mock, public_id_mock, storage_get_mock, sign_mock, get_location_mock
    ):
        broadcast_processor.VERIFICATION_NOTIFICATION = {"all": ["url1"]}
        fake_session = AsyncMock(post=AsyncMock())
        await broadcast_processor.process_verification_notifications(fake_session)
        fake_session.post.assert_called_once_with(
            data=b"location-object-bytes", headers={"dragonchainId": "my-public-id", "signature": "my-signature"}, timeout=30, url="url1"
        )
        srem_mock.assert_called_once_with("broadcast:notifications", "BLOCK/banana-l2-whatever")

    @patch(
        "dragonchain.broadcast_processor.broadcast_functions.get_notification_verifications_for_broadcast_async",
        return_value={"BLOCK/banana-l2-whatever"},
    )
    @patch("dragonchain.broadcast_processor.broadcast_processor.sign", return_value="my-signature")
    @patch("dragonchain.broadcast_processor.broadcast_processor.storage.get", return_value=b"location-object-bytes")
    @patch("dragonchain.broadcast_processor.broadcast_processor.keys.get_public_id", return_value="my-public-id")
    @patch("dragonchain.broadcast_processor.broadcast_functions.redis.srem_async", return_value="OK")
    async def test_process_verification_notification_removes_from_set_when_fail(
        self, srem_mock, public_id_mock, storage_get_mock, sign_mock, get_location_mock
    ):
        broadcast_processor.VERIFICATION_NOTIFICATION = {"all": ["url1"]}
        fake_session = AsyncMock(post=AsyncMock(side_effect=Exception("boom")))
        await broadcast_processor.process_verification_notifications(fake_session)
        fake_session.post.assert_called_once_with(
            data=b"location-object-bytes", headers={"dragonchainId": "my-public-id", "signature": "my-signature"}, timeout=30, url="url1"
        )
        srem_mock.assert_called_once_with("broadcast:notifications", "BLOCK/banana-l2-whatever")

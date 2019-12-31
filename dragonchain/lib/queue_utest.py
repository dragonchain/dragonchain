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

import json
import unittest
from unittest.mock import patch, MagicMock, call

from dragonchain.lib import queue
from dragonchain import exceptions
from dragonchain import test_env  # noqa: F401


class TestQueue(unittest.TestCase):
    @patch("dragonchain.lib.queue.redis")
    def test_remove_transaction_stubs(self, stub_redis):
        stub_transaction = MagicMock(txn_id="thing")
        queue.remove_transaction_stubs([stub_transaction])
        stub_redis.srem_sync.assert_called_once_with(queue.TEMPORARY_TX_KEY, "thing")

    def test_get_new_transaction_raises_on_bad_level(self):
        queue.LEVEL = "2"
        self.assertRaises(RuntimeError, queue.get_new_transactions)
        queue.LEVEL = "1"

    def test_get_next_l1_block_raises_on_bad_level(self):
        self.assertRaises(RuntimeError, queue.get_next_l1_block)

    def test_get_next_l2_blocks_raises_on_bad_level(self):
        self.assertRaises(RuntimeError, queue.get_next_l2_blocks)

    def test_get_next_l3_block_raises_on_bad_level(self):
        self.assertRaises(RuntimeError, queue.get_next_l3_block)

    def test_get_new_l4_blocks_raises_on_bad_level(self):
        self.assertRaises(RuntimeError, queue.get_new_l4_blocks)

    @patch("dragonchain.lib.queue.transaction_model.new_from_queue_input", return_value="fake model")
    @patch("dragonchain.lib.queue.redis")
    def test_get_new_transactions(self, mock_redis, mock_new_from_queue):
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = [json.dumps({"some": "data"}).encode("utf8")]
        mock_redis.llen_sync.return_value = 1
        mock_redis.pipeline_sync.return_value = mock_pipeline

        self.assertEqual(queue.get_new_transactions(), ["fake model"])

        mock_pipeline.rpoplpush.assert_called_once_with(queue.INCOMING_TX_KEY, queue.PROCESSING_TX_KEY)
        mock_new_from_queue.assert_called_once_with({"some": "data"})

    @patch("dragonchain.lib.queue.transaction_type_dao.get_registered_transaction_type", side_effect=exceptions.NotFound)
    @patch("dragonchain.lib.queue.redis")
    def test_enqueue_l1_raises_invalid_transaction_type_when_not_found(self, mock_redis, mock_get_transaction_type):
        self.assertRaises(exceptions.InvalidTransactionType, queue.enqueue_l1, {"header": {"txn_type": "banana"}})
        mock_get_transaction_type.assert_called_once_with("banana")

    @patch("dragonchain.lib.queue.transaction_type_dao.get_registered_transaction_type")
    @patch("dragonchain.lib.queue.redis")
    def test_enqueue_l1_not_invocation_is_successful(self, mock_redis, mock_get_transaction_type):
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = [1, 1]
        mock_redis.pipeline_sync.return_value = mock_pipeline

        param_value = {"header": {"txn_type": "thing", "txn_id": "some id", "invoker": "banana"}}
        queue.enqueue_l1(param_value)
        mock_get_transaction_type.assert_called_once_with("thing")
        mock_pipeline.lpush.assert_called_once_with(queue.INCOMING_TX_KEY, json.dumps(param_value, separators=(",", ":")))
        mock_pipeline.sadd.assert_called_once_with(queue.TEMPORARY_TX_KEY, "some id")
        mock_pipeline.execute.assert_called_once()

    @patch("dragonchain.lib.queue.transaction_type_dao.get_registered_transaction_type")
    @patch("dragonchain.lib.queue.redis")
    def test_enqueue_l1_raises_runtime_with_bad_redis_call(self, mock_redis, mock_get_transaction_type):
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = [1, 0]
        mock_redis.pipeline_sync.return_value = mock_pipeline

        param_value = {"header": {"txn_type": "thing", "txn_id": "some id", "invoker": "banana"}}
        self.assertRaises(RuntimeError, queue.enqueue_l1, param_value)

    @patch(
        "dragonchain.lib.queue.smart_contract_dao.get_contract_by_id",
        return_value=MagicMock(status={"state": "active"}, export_as_invoke_request=MagicMock(return_value={"some": "data"})),
    )
    @patch("dragonchain.lib.queue.transaction_type_dao.get_registered_transaction_type", return_value=MagicMock(contract_id="banana"))
    @patch("dragonchain.lib.queue.redis")
    def test_enqueue_l1_with_active_contract_invocation_attempt_is_successful(self, mock_redis, mock_get_transaction_type, mock_get_contract):
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = [1, 1, 1]
        mock_redis.pipeline_sync.return_value = mock_pipeline

        param_value = {"header": {"txn_type": "thing", "txn_id": "some id"}, "payload": '{"some":"stuff"}'}
        queue.enqueue_l1(param_value)
        mock_get_contract.assert_called_once_with("banana")
        param_value["payload"] = '{"some":"stuff"}'
        mock_pipeline.lpush.assert_has_calls(
            [
                call(queue.INCOMING_TX_KEY, json.dumps(param_value, separators=(",", ":"))),
                call(queue.CONTRACT_INVOKE_MQ_KEY, json.dumps({"some": "data"}, separators=(",", ":"))),
            ]
        )

    @patch("dragonchain.lib.queue.smart_contract_dao.get_contract_by_id", return_value=MagicMock(status={"state": "inactive"}))
    @patch("dragonchain.lib.queue.transaction_type_dao.get_registered_transaction_type", return_value=MagicMock(contract_id="banana"))
    @patch("dragonchain.lib.queue.redis")
    def test_enqueue_l1_with_inactive_contract_invocation_attempt_is_successful(self, mock_redis, mock_get_transaction_type, mock_get_contract):
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = [1, 1]
        mock_redis.pipeline_sync.return_value = mock_pipeline

        queue.enqueue_l1({"header": {"txn_type": "thing", "txn_id": "some id"}})
        mock_get_contract.assert_called_once_with("banana")
        mock_pipeline.lpush.assert_called_once()
        mock_pipeline.sadd.assert_called_once()

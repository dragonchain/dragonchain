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
from unittest.mock import patch, MagicMock

from dragonchain import test_env  # noqa: F401
from dragonchain import exceptions
from dragonchain.webserver.lib import transactions


class TestQueryTransactions(unittest.TestCase):
    @patch("dragonchain.lib.database.redisearch.search")
    def test_query_transactions_calls_search(self, mock_get_txn):
        transactions.query_transactions_v1({"transaction_type": "banana", "q": "*"}, False)
        mock_get_txn.assert_called_with(
            index="banana", limit=None, offset=None, only_id=None, query_str="*", sort_asc=None, sort_by=None, verbatim=None
        )

    @patch("dragonchain.webserver.lib.transactions.storage.select_transaction", return_value="a txn")
    @patch(
        "dragonchain.webserver.lib.transactions.redisearch.search", return_value=MagicMock(docs=[MagicMock(id="fake", block_id="banana")], total=4)
    )
    def test_query_transactions_returns_search_result(self, mock_search, mock_select):
        response = transactions.query_transactions_v1({"transaction_type": "banana", "q": "query"}, False)
        self.assertEqual(response, {"total": 4, "results": ["a txn"]})

        mock_search.assert_called_once()
        mock_select.assert_called_once()


class TestGetTransactions(unittest.TestCase):
    @patch("dragonchain.lib.database.redis.sismember_sync", return_value=True)
    def test_get_transaction_v1_returns_stub(self, mock_sismember):
        result = transactions.get_transaction_v1("banana", True)
        self.assertEqual(
            result, {"header": {"txn_id": "banana"}, "status": "pending", "message": "This transaction is waiting to be included in a block"}
        )

    @patch("dragonchain.lib.database.redis.sismember_sync", return_value=False)
    @patch("dragonchain.lib.database.redisearch.search", return_value=MagicMock(block_id="banana"))
    @patch("dragonchain.lib.interfaces.storage.select_transaction", return_value={"payload": '{"banana":4}'})
    def test_get_transaction_v1_returns_parsed(self, mock_sismember, mock_search, mock_select_txn):
        result = transactions.get_transaction_v1("banana", True)
        self.assertEqual(result["payload"], {"banana": 4})


class TestSubmitTransactions(unittest.TestCase):
    @patch("dragonchain.webserver.lib.transactions._generate_transaction_model")
    @patch("dragonchain.webserver.lib.transactions.queue")
    def test_submit_transaction_checks_if_key_is_allowed(self, mock_queue, mock_gen_model):
        mock_key = MagicMock()
        mock_key.is_key_allowed.return_value = True
        transactions.submit_transaction_v1({}, None, api_key=mock_key)
        mock_key.is_key_allowed.assert_called_once()
        mock_key.is_key_allowed.return_value = False
        self.assertRaises(exceptions.ActionForbidden, transactions.submit_transaction_v1, {}, None, api_key=mock_key)

    @patch("dragonchain.webserver.lib.transactions._generate_transaction_model")
    @patch("dragonchain.webserver.lib.transactions.queue")
    @patch("dragonchain.webserver.lib.transactions.dc_redis")
    def test_submit_transaction_bulk_checks_if_key_is_allowed(self, mock_queue, mock_gen_model, mock_redis):
        mock_key = MagicMock()
        mock_key.is_key_allowed.return_value = True
        transactions.submit_bulk_transaction_v1([{"txn_type": "whatever"}], api_key=mock_key)
        mock_key.is_key_allowed.assert_called_once()
        mock_key.is_key_allowed.return_value = False
        self.assertRaises(exceptions.ActionForbidden, transactions.submit_bulk_transaction_v1, [{"txn_type": "whatever"}], api_key=mock_key)

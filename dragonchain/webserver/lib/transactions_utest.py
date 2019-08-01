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
from unittest.mock import patch

from dragonchain import test_env  # noqa: F401
from dragonchain.webserver.lib import transactions


class TestQueryTransactions(unittest.TestCase):
    @patch("dragonchain.webserver.lib.transactions._search_transaction")
    def test_query_transactions_calls_search(self, mock_get_txn):
        transactions.query_transactions_v1(None, False)
        mock_get_txn.assert_called_with(q="*", sort="block_id:desc", should_parse=False)

    @patch("dragonchain.webserver.lib.transactions._search_transaction", return_value={"fake": "result"})
    def test_query_transactions_returns_search_result(self, mock_search):
        response = transactions.query_transactions_v1(None, False)
        self.assertEqual(response, {"fake": "result"})

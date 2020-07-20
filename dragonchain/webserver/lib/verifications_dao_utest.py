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
from unittest.mock import patch, call, MagicMock

from dragonchain import test_env  # noqa: F401
from dragonchain import exceptions
from dragonchain.webserver.lib import verifications
from dragonchain.lib.database import redisearch


class TestVerificationDAO(unittest.TestCase):
    @patch(
        "dragonchain.webserver.lib.verifications.matchmaking.get_claim_check",
        return_value={
            "validations": {
                "l2": {"l2chain1": "data", "l2chain2": "data"},
                "l3": {"l3chain": "data"},
                "l4": {"l4chain": "data"},
                "l5": {"l5chain": "data"},
            }
        },
    )
    @patch(
        "dragonchain.webserver.lib.verifications.broadcast_functions.get_all_verifications_for_block_sync",
        return_value=[{"l2chain1"}, {"l3chain"}, set(), set()],
    )
    def test_get_pending_verifications(self, mock_get_verifications, mock_get_claim_check):
        block_id = "123"
        self.assertEqual(verifications.get_pending_verifications_v1(block_id), {"2": ["l2chain2"], "3": [], "4": ["l4chain"], "5": ["l5chain"]})
        mock_get_claim_check.assert_called_once_with(block_id)
        mock_get_verifications.assert_called_once_with(block_id)

    @patch("dragonchain.webserver.lib.verifications._level_records")
    @patch("dragonchain.webserver.lib.verifications._all_records")
    def test_get_verifications_records_on_specific_level(self, mock_all_records, mock_level_records):
        verifications._get_verification_records(1, 2)
        mock_level_records.assert_called_once_with(1, 2)
        mock_all_records.assert_not_called()

    @patch("dragonchain.webserver.lib.verifications._level_records")
    @patch("dragonchain.webserver.lib.verifications._all_records")
    def test_get_verifications_records_generalized(self, mock_all_records, mock_level_records):
        verifications._get_verification_records(1)
        mock_level_records.assert_not_called()
        mock_all_records.assert_called_once_with(1)

    @patch("dragonchain.webserver.lib.verifications._level_records")
    @patch("dragonchain.webserver.lib.verifications._all_records")
    def test_get_verifications_records_raises_invalid_node_level(self, mock_all_records, mock_level_records):
        self.assertRaises(exceptions.InvalidNodeLevel, verifications._get_verification_records, 1, 50)
        self.assertRaises(exceptions.InvalidNodeLevel, verifications._get_verification_records, 1, 1)

    @patch("dragonchain.webserver.lib.verifications.storage.list_objects", return_value=["BLOCK/21428048-l2-2cf71328-b1e3-4180-911d-2c40c0e5aac2"])
    @patch("dragonchain.webserver.lib.verifications.storage.get_json_from_object", return_value="return")
    def test__level_records_returns_correctly(self, mock_get, mock_list):
        self.assertEqual(verifications._level_records(1, 2), ["return"])
        mock_list.assert_called_once_with("BLOCK/1-l2")
        mock_get.assert_called_once_with("BLOCK/21428048-l2-2cf71328-b1e3-4180-911d-2c40c0e5aac2")

    @patch("dragonchain.webserver.lib.verifications._level_records", return_value=["return"])
    def test__all_records_returns_correctly(self, mock_level_records):
        self.assertEqual(verifications._all_records(1), {"2": ["return"], "3": ["return"], "4": ["return"], "5": ["return"]})
        mock_level_records.assert_has_calls([call(1, 2), call(1, 3), call(1, 4), call(1, 5)])

    @patch("dragonchain.lib.database.redisearch.search", return_value=MagicMock(docs=[MagicMock(id="banana")]))
    def test__query_l5_verifications_returns_correctly(self, mock_redisearch_search):
        self.assertEqual(verifications._query_l5_verification("banana", "123456789"), "banana")
        mock_redisearch_search.assert_called_once_with(
            index="ver", query_str="@dc_id:{banana} @timestamp:[123456790 +inf]", only_id=True, limit=1, sort_by="timestamp", sort_asc=True
        )

    @patch("dragonchain.lib.database.redisearch.search", return_value=MagicMock(docs=[]))
    def test__query_l5_verifications_returns_correctly_when_no_results_found(self, mock_redisearch_search):
        self.assertIsNone(verifications._query_l5_verification("banana", "123456789"))
        mock_redisearch_search.assert_called_once_with(
            index="ver", query_str="@dc_id:{banana} @timestamp:[123456790 +inf]", only_id=True, limit=1, sort_by="timestamp", sort_asc=True
        )

    @patch("dragonchain.webserver.lib.verifications._get_verification_records", return_value=[])
    def test_query_interchain_broadcasts_v1_returns_correctly_when_block_id_doesnt_exist(self, mock_get_verification_records):
        self.assertEqual(verifications.query_interchain_broadcasts_v1("123"), [])
        mock_get_verification_records.assert_called_once_with("123", 5)

    @patch("dragonchain.webserver.lib.verifications._query_l5_verification", return_value="banana")
    @patch(
        "dragonchain.webserver.lib.verifications._get_verification_records", return_value=[{"header": {"dc_id": "banana", "timestamp": "12345987"}}]
    )
    @patch("dragonchain.webserver.lib.verifications.storage.get_json_from_object", return_value="return")
    def test_query_interchain_broadcasts_v1_returns_correctly(self, mock_get_object, mock_get_verification_records, mock_query_l5_verifications):
        mock_redis = MagicMock(smembers=MagicMock(return_value=[b"mydragonchain"]))
        redisearch._get_redisearch_index_client = MagicMock(return_value=MagicMock(redis=mock_redis))
        self.assertEqual(verifications.query_interchain_broadcasts_v1("12345"), [{"header": {"dc_id": "banana", "timestamp": "12345987"}}, "return"])
        mock_query_l5_verifications.assert_called_once_with("mydragonchain", "12345987")
        mock_get_object.assert_called_once_with("BLOCK/banana")

    @patch("dragonchain.webserver.lib.verifications._query_l5_verification", return_value=None)
    @patch(
        "dragonchain.webserver.lib.verifications._get_verification_records", return_value=[{"header": {"dc_id": "banana", "timestamp": "12345987"}}]
    )
    @patch("dragonchain.webserver.lib.verifications.storage.get_json_from_object")
    def test_query_interchain_broadcasts_v1_returns_correctly_when_verification_not_found(
        self, mock_get_object, mock_get_verification_records, mock_query_l5_verifications
    ):
        mock_redis = MagicMock(smembers=MagicMock(return_value=[b"mydragonchain"]))
        redisearch._get_redisearch_index_client = MagicMock(return_value=MagicMock(redis=mock_redis))
        self.assertEqual(verifications.query_interchain_broadcasts_v1("12345"), [{"header": {"dc_id": "banana", "timestamp": "12345987"}}])
        mock_query_l5_verifications.assert_called_once_with("mydragonchain", "12345987")
        mock_get_object.assert_not_called()

    @patch("dragonchain.webserver.lib.verifications._query_l5_verification", return_value=None)
    @patch("dragonchain.webserver.lib.verifications._get_verification_records", return_value=[])
    @patch("dragonchain.webserver.lib.verifications.storage.get_json_from_object")
    def test_query_interchain_broadcasts_v1_returns_correctly_when_block_doesnt_exist(
        self, mock_get_object, mock_get_verification_records, mock_query_l5_verifications
    ):
        mock_redis = MagicMock(smembers=MagicMock(return_value=[b"mydragonchain"]))
        redisearch._get_redisearch_index_client = MagicMock(return_value=MagicMock(redis=mock_redis))
        self.assertEqual(verifications.query_interchain_broadcasts_v1("12345"), [])
        mock_query_l5_verifications.assert_not_called()
        mock_get_object.assert_not_called()

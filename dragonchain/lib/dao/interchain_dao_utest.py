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
from unittest.mock import patch, call, MagicMock

from dragonchain import test_env  # noqa: F401
from dragonchain import exceptions
from dragonchain.lib.dao import interchain_dao


class TestTransactionTypeDAO(unittest.TestCase):
    @patch("dragonchain.lib.interfaces.storage.put_object_as_json")
    def test_save_interchain_client_calls_correct_functions(self, patch_save):
        fake_interchain = MagicMock()
        fake_interchain.export_as_at_rest.return_value = "banana"
        interchain_dao.save_interchain_client(fake_interchain)
        fake_interchain.export_as_at_rest.assert_called_once()
        patch_save.assert_called_once_with(f"INTERCHAINS/{fake_interchain.blockchain}/{fake_interchain.name}", "banana")

    @patch("dragonchain.lib.interfaces.storage.does_object_exist", return_value=True)
    def test_does_interchain_exist_returns_true(self, mock_exist):
        self.assertTrue(interchain_dao.does_interchain_exist("bitcoin", "whatever"))
        self.assertTrue(interchain_dao.does_interchain_exist("ethereum", "whatever"))

    @patch("dragonchain.lib.interfaces.storage.does_object_exist", return_value=False)
    def test_does_interchain_exist_returns_false(self, mock_exist):
        self.assertFalse(interchain_dao.does_interchain_exist("bitcoin", "whatever"))
        self.assertFalse(interchain_dao.does_interchain_exist("ethereum", "whatever"))

    def test_does_interchain_exist_returns_false_with_bad_blockchain(self):
        self.assertFalse(interchain_dao.does_interchain_exist("badblockchaintype", "whatever"))

    @patch("dragonchain.lib.interfaces.storage.get_json_from_object", return_value="thing")
    @patch("dragonchain.lib.dto.eth.new_from_at_rest")
    @patch("dragonchain.lib.dto.btc.new_from_at_rest")
    def test_get_interchain_client_gets_from_storage(self, mock_btc, mock_eth, mock_storage):
        interchain_dao.get_interchain_client("bitcoin", "banana")
        interchain_dao.get_interchain_client("ethereum", "banana")
        mock_btc.assert_called_once_with("thing")
        mock_eth.assert_called_once_with("thing")
        mock_storage.assert_has_calls([call("INTERCHAINS/bitcoin/banana"), call("INTERCHAINS/ethereum/banana")])

    def test_get_interchain_client_throws_with_unknown_network(self):
        self.assertRaises(exceptions.NotFound, interchain_dao.get_interchain_client, "banana", "soup")

    @patch("dragonchain.lib.interfaces.storage.list_objects", return_value=["a"])
    @patch("dragonchain.lib.interfaces.storage.get_json_from_object", return_value="thing")
    @patch("dragonchain.lib.dto.btc.new_from_at_rest", return_value="whatever1")
    def test_list_interchain_client_bitcoin_calls_correct_functions(self, mock_btc, mock_get, mock_list):
        self.assertEqual(["whatever1"], interchain_dao.list_interchain_clients("bitcoin"))
        mock_btc.assert_called_once_with("thing")
        mock_list.assert_called_once_with("INTERCHAINS/bitcoin/")
        mock_get.assert_called_once_with("a")

    @patch("dragonchain.lib.interfaces.storage.list_objects", return_value=["a"])
    @patch("dragonchain.lib.interfaces.storage.get_json_from_object", return_value="thing")
    @patch("dragonchain.lib.dto.eth.new_from_at_rest", return_value="whatever1")
    def test_list_interchain_client_ethereum_calls_correct_functions(self, mock_eth, mock_get, mock_list):
        self.assertEqual(["whatever1"], interchain_dao.list_interchain_clients("ethereum"))
        mock_eth.assert_called_once_with("thing")
        mock_list.assert_called_once_with("INTERCHAINS/ethereum/")
        mock_get.assert_called_once_with("a")

    def test_list_interchain_throws_with_unknown_network(self):
        self.assertRaises(exceptions.NotFound, interchain_dao.list_interchain_clients, "soup")

    @patch("dragonchain.lib.interfaces.storage.put_object_as_json")
    @patch("dragonchain.lib.dao.interchain_dao.get_interchain_client")
    def test_set_default_interchain_calls_storage(self, mock_get_client, mock_put_object):
        interchain_dao.set_default_interchain_client("something", "awful")
        mock_get_client.assert_called_once_with("something", "awful")
        mock_put_object.assert_called_once_with("INTERCHAINS/default", {"version": "1", "blockchain": "something", "name": "awful"})

    @patch("dragonchain.lib.dao.interchain_dao.get_interchain_client", return_value="yes")
    @patch("dragonchain.lib.interfaces.storage.get_json_from_object", return_value={"blockchain": "thing", "name": "something", "version": "1"})
    def test_get_default_client_gets_from_storage(self, mock_get_storage, mock_get_interchain_client):
        self.assertEqual(interchain_dao.get_default_interchain_client(), "yes")
        mock_get_storage.assert_called_once_with("INTERCHAINS/default")
        mock_get_interchain_client.assert_called_once_with("thing", "something")

    @patch("dragonchain.lib.interfaces.storage.get_json_from_object", return_value={"version": "banana"})
    def test_get_default_client_raises_with_unkown_version(self, mock_get_storage):
        self.assertRaises(NotImplementedError, interchain_dao.get_default_interchain_client)

    @patch("dragonchain.lib.interfaces.storage.delete")
    def test_delete_interchain(self, mock_delete):
        interchain_dao.delete_interchain_client("greater", "good")
        mock_delete.assert_called_once_with("INTERCHAINS/greater/good")

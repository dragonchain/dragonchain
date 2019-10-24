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
from dragonchain.webserver.lib import interchain


class TestInterchain(unittest.TestCase):
    def test_get_output_dto_v1_ethereum(self):
        fake_client = MagicMock(blockchain="ethereum")
        self.assertEqual(
            interchain._get_output_dto_v1(fake_client),
            {
                "version": "1",
                "blockchain": "ethereum",
                "name": fake_client.name,
                "rpc_address": fake_client.rpc_address,
                "chain_id": fake_client.chain_id,
                "address": fake_client.address,
            },
        )

    def test_get_output_dto_v1_bitcoin(self):
        fake_client = MagicMock(blockchain="bitcoin")
        self.assertEqual(
            interchain._get_output_dto_v1(fake_client),
            {
                "version": "1",
                "blockchain": "bitcoin",
                "name": fake_client.name,
                "rpc_address": fake_client.rpc_address,
                "testnet": fake_client.testnet,
                "address": fake_client.address,
            },
        )

    def test_get_output_dto_v1_bad_data(self):
        fake_client = MagicMock(blockchain="doesntexist")
        self.assertRaises(RuntimeError, interchain._get_output_dto_v1, fake_client)

    @patch("dragonchain.lib.dao.interchain_dao.get_interchain_client")
    @patch("dragonchain.webserver.lib.interchain._get_output_dto_v1", return_value="blah")
    def test_get_interchain_v1(self, mock_get_output, mock_get_client):
        self.assertEqual(interchain.get_interchain_v1("a", "b"), "blah")
        mock_get_client.assert_called_once_with("a", "b")
        mock_get_output.assert_called_once_with(mock_get_client.return_value)

    @patch("dragonchain.lib.dao.interchain_dao.get_interchain_client")
    def test_sign_interchain_v1(self, mock_get_client):
        interchain.sign_interchain_transaction_v1("bitcoin", "name", {"some": "data"})
        mock_get_client.return_value.sign_transaction.assert_called_once_with({"some": "data"})

    @patch("dragonchain.lib.dao.interchain_dao.get_default_interchain_client", return_value="banana")
    @patch("dragonchain.webserver.lib.interchain._get_output_dto_v1", return_value="blah")
    def test_get_default_interchain(self, mock_get_output, mock_get_interchain):
        self.assertEqual(interchain.get_default_interchain_v1(), "blah")
        mock_get_output.assert_called_once_with("banana")
        mock_get_interchain.assert_called_once()

    @patch("dragonchain.lib.dao.interchain_dao.set_default_interchain_client", return_value="banana")
    @patch("dragonchain.webserver.lib.interchain._get_output_dto_v1", return_value="blah")
    def test_set_default_interchain(self, mock_get_output, mock_set_default):
        self.assertEqual(interchain.set_default_interchain_v1("thing1", "thing2"), "blah")
        mock_get_output.assert_called_once_with("banana")
        mock_set_default.assert_called_once_with("thing1", "thing2")

    @patch("dragonchain.lib.dao.interchain_dao.delete_interchain_client")
    def test_delete_interchain(self, mock_delete):
        interchain.delete_interchain_v1("a", "b")
        mock_delete.assert_called_once_with("a", "b")

    @patch("dragonchain.lib.dao.interchain_dao.list_interchain_clients", return_value=[MagicMock()])
    @patch("dragonchain.webserver.lib.interchain._get_output_dto_v1", return_value="blah")
    def test_list_interchain(self, mock_get_output, mock_list):
        self.assertEqual(interchain.list_interchain_v1("test"), {"interchains": ["blah"]})
        mock_get_output.assert_called_once()
        mock_list.assert_called_once_with("test")

    @patch("dragonchain.lib.dto.btc.new_from_user_input")
    @patch("dragonchain.lib.dao.interchain_dao.save_interchain_client")
    @patch("dragonchain.lib.dao.interchain_dao.does_interchain_exist", return_value=False)
    @patch("dragonchain.webserver.lib.interchain._get_output_dto_v1", return_value="blah")
    def test_create_interchain_bitcoin(self, mock_get_output, mock_exist, mock_save_client, mock_new_from_user):
        self.assertEqual(interchain.create_bitcoin_interchain_v1({"thing": "ok"}), "blah")
        mock_new_from_user.assert_called_once_with({"thing": "ok"})
        mock_save_client.assert_called_once_with(mock_new_from_user.return_value)
        mock_get_output.assert_called_once_with(mock_new_from_user.return_value)

    @patch("dragonchain.lib.dto.btc.new_from_user_input")
    @patch("dragonchain.lib.dao.interchain_dao.does_interchain_exist", return_value=True)
    def test_create_interchain_bitcoin_throws_if_already_exists(self, mock_exist, mock_new_from_user):
        self.assertRaises(exceptions.InterchainConflict, interchain.create_bitcoin_interchain_v1, {})
        mock_new_from_user.assert_called_once_with({})
        mock_exist.assert_called_once()

    @patch("dragonchain.lib.dto.eth.new_from_user_input")
    @patch("dragonchain.lib.dao.interchain_dao.save_interchain_client")
    @patch("dragonchain.lib.dao.interchain_dao.does_interchain_exist", return_value=False)
    @patch("dragonchain.webserver.lib.interchain._get_output_dto_v1", return_value="blah")
    def test_create_interchain_ethereum(self, mock_get_output, mock_exist, mock_save_client, mock_new_from_user):
        self.assertEqual(interchain.create_ethereum_interchain_v1({"thing": "ok"}), "blah")
        mock_new_from_user.assert_called_once_with({"thing": "ok"})
        mock_save_client.assert_called_once_with(mock_new_from_user.return_value)
        mock_get_output.assert_called_once_with(mock_new_from_user.return_value)

    @patch("dragonchain.lib.dto.eth.new_from_user_input")
    @patch("dragonchain.lib.dao.interchain_dao.does_interchain_exist", return_value=True)
    def test_create_interchain_ethereum_throws_if_already_exists(self, mock_exist, mock_new_from_user):
        self.assertRaises(exceptions.InterchainConflict, interchain.create_ethereum_interchain_v1, {})
        mock_new_from_user.assert_called_once_with({})
        mock_exist.assert_called_once()

    @patch("dragonchain.webserver.lib.interchain.create_bitcoin_interchain_v1", return_value="cool")
    @patch("dragonchain.lib.dao.interchain_dao.get_interchain_client")
    def test_update_interchain_bitcoin_calls_correctly(self, mock_get_interchain, mock_create_bitcoin):
        self.assertEqual(interchain.update_bitcoin_interchain_v1("thing", {"rpc_address": "overwritten"}), "cool")
        mock_get_interchain.assert_called_once_with("bitcoin", "thing")
        mock_create_bitcoin.assert_called_once_with(
            {
                "version": "1",
                "name": "thing",
                "testnet": mock_get_interchain.return_value.testnet,
                "private_key": mock_get_interchain.return_value.get_private_key(),
                "rpc_address": "overwritten",
                "rpc_authorization": mock_get_interchain.return_value.authorization,
                "utxo_scan": False,
            },
            conflict_check=False,
        )

    @patch("dragonchain.webserver.lib.interchain.create_ethereum_interchain_v1", return_value="cool")
    @patch("dragonchain.lib.dao.interchain_dao.get_interchain_client")
    def test_update_interchain_ethereum_calls_correctly(self, mock_get_interchain, mock_create_ethereum):
        self.assertEqual(interchain.update_ethereum_interchain_v1("thing", {"rpc_address": "overwritten"}), "cool")
        mock_get_interchain.assert_called_once_with("ethereum", "thing")
        mock_create_ethereum.assert_called_once_with(
            {
                "version": "1",
                "name": "thing",
                "private_key": mock_get_interchain.return_value.get_private_key(),
                "rpc_address": "overwritten",
                "chain_id": mock_get_interchain.return_value.chain_id,
            },
            conflict_check=False,
        )

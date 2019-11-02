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

import base64
import unittest
from unittest.mock import MagicMock, patch

import requests

from dragonchain import exceptions
from dragonchain import test_env  # noqa: F401
from dragonchain.lib.dto import bnb


class TestBinanceMethods(unittest.TestCase):
    def setUp(self):
        # private_key = "495bb2a3f229eb0abb2bf71a3dca56b31d60c128dfd81e9e907e5eedb67f19a0"
        b64_private_key = "SVuyo/Ip6wq7K/caPcpWsx1gwSjf2B6ekH5e7bZ/GaA="
        self.client = bnb.BinanceNetwork("banana", True, "b.a.n.a.n.a", 27147, 1169, b64_private_key)

    def test_new_from_at_rest_good_input_v1(self):
        client = bnb.new_from_at_rest(
            {
                "version": "1",
                "name": "banana",
                "node_url": "b.a.n.a.n.a",
                "rpc_port": 27147,
                "api_port": 1169,
                "testnet": True,
                "private_key": "SVuyo/Ip6wq7K/caPcpWsx1gwSjf2B6ekH5e7bZ/GaA=",
            }
        )
        self.assertEqual(client.name, "banana")
        self.assertEqual(client.node_url, "b.a.n.a.n.a")
        self.assertEqual(client.rpc_port, 27147)
        self.assertEqual(client.api_port, 1169)
        self.assertTrue(client.testnet)
        self.assertEqual(client.address, "tbnb1u06kxdru0we8at0ktd6q4c5qk80zwdyvhzrulk")

    def test_new_from_at_rest_bad_version(self):
        self.assertRaises(NotImplementedError, bnb.new_from_at_rest, {"version": "1337"})  # good is "1"

    # TODO: check that this is failing in the RIGHT way -- think I'm not passing args right
    # shouldn't it be bnb.new_from_user_input(args)?
    def test_new_from_user_input_throws_with_bad_version(self):
        self.assertRaises(exceptions.BadRequest, bnb.new_from_user_input, {"version": "99999"})  # good is "1"

    def test_should_retry_broadcast_true(self):
        self.client.get_current_block = MagicMock(return_value=100)
        self.assertTrue(self.client.should_retry_broadcast(1))
        self.client.get_current_block.assert_called_once()

    def test_should_retry_broadcast_false(self):
        self.client.get_current_block = MagicMock(return_value=100)
        self.assertFalse(self.client.should_retry_broadcast(99))
        self.client.get_current_block.assert_called_once()

    @patch("binance_transaction.BnbTransaction.encode", return_value=b"fake_encoded_txn")
    def test_sign_transaction(self, mock_encode):
        random_addy = "bnb1l09g77u8wslyg9vjza3rfgmq776jy2lt8gtmvm"
        inputs = {"address": random_addy, "coins": [{"amount": 0, "denom": "BNB"}]}
        outputs = {"address": random_addy, "coins": [{"amount": 0, "denom": "BNB"}]}
        fake_raw_txn = {
            "account_number": 123456,
            "sequence": 123,
            "from": random_addy,
            "memo": "fake_DC_L5_transaction_hash",
            "msgs": [{"type": "cosmos-sdk/Send", "inputs": [inputs], "outputs": [outputs]}],
        }
        response = self.client.sign_transaction(fake_raw_txn)
        self.assertEqual(response, "ZmFrZV9lbmNvZGVkX3R4bg==")
        mock_encode.assert_called_once()

    def test_publish_transaction(self):
        fake_response = requests.Response()
        fake_response._content = b'{"result": {"hash": "BOGUS_RESULT_HASH"}}'
        self.client._build_transaction_msg = MagicMock(return_value={"built_tx": "fake"})
        self.client.sign_transaction = MagicMock(return_value="signed_tx")
        fake_acct = requests.Response()
        fake_acct._content = b'{"sequence": 0, "account_number": 12345}'
        self.client._call_node_api = MagicMock(return_value=fake_acct)
        self.client._call_node_rpc = MagicMock(return_value=fake_response)
        response = self.client._publish_transaction("DC-L5:_fake_L5_block_hash")
        self.assertEqual(response, "BOGUS_RESULT_HASH")
        self.client._call_node_rpc.assert_called_once_with("broadcast_tx_commit", {"tx": "signed_tx"})

    def test_get_current_block(self):
        fake_response = requests.Response()
        fake_response._content = b'{"result": {"block": {"header": {"height": 12345678}}}}'
        self.client._call_node_rpc = MagicMock(return_value=fake_response)
        response = self.client.get_current_block()
        self.assertEqual(response, 12345678)
        self.client._call_node_rpc.assert_called_once_with("block", {})

    def test_check_balance_success(self):
        fake_response = requests.Response()
        fake_response._content = b'{"balance": {"free": 1234567890}}'
        api_string = "balances/tbnb1u06kxdru0we8at0ktd6q4c5qk80zwdyvhzrulk/BNB"
        self.client._call_node_api = MagicMock(return_value=fake_response)
        response = self.client.check_balance()
        self.assertEqual(response, 1234567890)
        self.client._call_node_api.assert_called_once_with(api_string)

    # TODO: needs coverage of a 0 balance response
    def test_check_balance_failure(self):
        pass

    def test_get_transaction_fee_estimnate_success(self):
        fake_response = requests.Response()
        fake_response._content = b'[{}, {}, {"fixed_fee_params": {"msg_type": "send", "fee": 31337}}, {}, {}]'
        self.client._call_node_api = MagicMock(return_value=fake_response)
        response = self.client.get_transaction_fee_estimate()
        self.assertEqual(response, 31337)
        self.client._call_node_api.assert_called_once_with("fees")

    # TODO: needs coverage of a failed fetch
    def test_get_transaction_fee_estimate_failure(self):
        pass

    def test_is_transaction_confirmed_final(self):
        self.client.get_current_block = MagicMock(return_value=1245839)  # fake block number
        fake_response = requests.Response()
        fake_response._content = b'{"result": {"height": 1245739}}'
        self.client._call_node_rpc = MagicMock(return_value=fake_response)  # txn 100 blocks ago
        response = self.client.is_transaction_confirmed("46616b6554786e48617368")
        self.assertTrue(response)
        self.client._call_node_rpc.assert_called_once_with("tx", {"hash": "RmFrZVR4bkhhc2g=", "prove": True})
        self.client.get_current_block.assert_called_once()

    def test_is_transaction_confirmed_unconfirmed(self):
        self.client.get_current_block = MagicMock(return_value=1245839)  # fake block number
        fake_response = requests.Response()
        fake_response._content = b'{"result": {"height": 1245839}}'
        self.client._call_node_rpc = MagicMock(return_value=fake_response)  # txn in latest block
        response = self.client.is_transaction_confirmed("46616b6554786e48617368")
        self.assertFalse(response)
        self.client._call_node_rpc.assert_called_once_with("tx", {"hash": "RmFrZVR4bkhhc2g=", "prove": True})
        self.client.get_current_block.assert_called_once()

    def test_is_transaction_confirmed_error(self):
        fake_response = requests.Response()
        fake_response._content = b'{"error": {"data": "Tx (1245839) not found"}}'
        self.client._call_node_rpc = MagicMock(return_value=fake_response)
        self.assertRaises(exceptions.TransactionNotFound, self.client.is_transaction_confirmed, "46616b6554786e48617368")
        self.client._call_node_rpc.assert_called_once_with("tx", {"hash": "RmFrZVR4bkhhc2g=", "prove": True})

    def test_export_as_at_rest(self):
        self.assertEqual(
            self.client.export_as_at_rest(),
            {
                "version": "1",
                "blockchain": "binance",
                "name": "banana",
                "testnet": True,
                "node_url": "b.a.n.a.n.a",
                "rpc_port": 27147,
                "api_port": 1169,
                "private_key": "SVuyo/Ip6wq7K/caPcpWsx1gwSjf2B6ekH5e7bZ/GaA=",
            },
        )

    @patch("requests.post", return_value=MagicMock(status_code=200, json=MagicMock(return_value={"result": "MyResult"})))
    def test_rpc_request_success(self, mock_post):
        response = self.client._call_node_rpc("MyMethod", {"symbol": "BANANA"})
        self.assertEqual(response.json(), {"result": "MyResult"})
        mock_post.assert_called_once_with(
            "b.a.n.a.n.a:27147/", json={"method": "MyMethod", "jsonrpc": "2.0", "params": {"symbol": "BANANA"}, "id": "dontcare"}, timeout=30
        )

    @patch("requests.get", return_value=MagicMock(status_code=200, json=MagicMock(return_value={"result": "MyResult"})))
    def test_api_request_success(self, mock_get):
        response = self.client._call_node_api("MyPath")
        self.assertEqual(response.json(), {"result": "MyResult"})
        mock_get.assert_called_once_with("b.a.n.a.n.a:1169/api/v1/MyPath", timeout=30)

    # BROKEN:
    @patch("dragonchain.lib.dto.bnb.requests")
    def test_rpc_request_error(self, mock_requests):
        pass
        # mock_requests.post.side_effect = requests.exceptions.ConnectTimeout
        # self.assertRaises(exceptions.InterchainConnectionError, self.client._call_node_rpc, "MyMethod", {"symbol": "BANANA"})

    # BROKEN:
    @patch("dragonchain.lib.dto.bnb.requests")
    def test_api_request_error(self, mock_requests):
        pass
        # mock_requests.get.side_effect = requests.exceptions.ConnectTimeout
        # self.assertRaises(exceptions.InterchainConnectionError, self.client._call_node_api, "MyPath")

    def test_from_user_input_throws_with_bad_private_key(self):
        fake_input = {"version": "1", "testnet": True, "node_url": "b.a.n.a.n.a", "rpc_port": 27147, "api_port": 1169, "private_key": "badKey"}
        self.assertRaises(exceptions.BadRequest, bnb.new_from_user_input, fake_input)

    @patch("dragonchain.lib.dto.bnb.BinanceNetwork.ping")
    def test_from_user_input_works_with_no_provided_key(self, mock_ping):
        client = bnb.new_from_user_input(
            {"version": "1", "name": "no_private_key", "node_url": "b.a.n.a.n.a", "rpc_port": 27147, "api_port": 1169, "testnet": True}
        )
        mock_ping.assert_called_once()
        self.assertEqual(client.name, "no_private_key")
        self.assertEqual(client.node_url, "b.a.n.a.n.a")
        self.assertEqual(client.rpc_port, 27147)
        self.assertEqual(client.api_port, 1169)
        self.assertTrue(client.testnet)

    @patch("dragonchain.lib.dto.bnb.BinanceNetwork.ping")
    def test_new_from_user_input_sets_good_keys(self, mock_ping):
        # Good hex key without 0x
        privkey = "7796b9ac433fab2a83d281e8064f29c935133139b62ec52c8e73de28440c0dc6"
        client_a = bnb.new_from_user_input({"version": "1", "name": "banana", "testnet": True, "private_key": privkey})
        # Good hex key with 0x
        client_b = bnb.new_from_user_input({"version": "1", "name": "banana", "testnet": True, "private_key": f"0x{privkey}"})
        # Good key from mnemonic string
        mnemonic = ("banana " * 24).rstrip()
        client_c = bnb.new_from_user_input({"version": "1", "name": "banana", "testnet": True, "private_key": mnemonic})
        from_hex = b"w\x96\xb9\xacC?\xab*\x83\xd2\x81\xe8\x06O)\xc95\x1319\xb6.\xc5,\x8es\xde(D\x0c\r\xc6"
        from_mem = b"\xc6G\xd2\xdf\xdb\x97\xb3B`\x82Yx\xe7\x10\xf9g\x0bY\xc7o\xa8n\xd0m\xf7\x07\xadv'\t\x17_"
        self.assertEqual(base64.b64decode(client_a.b64_private_key), from_hex)
        self.assertEqual(base64.b64decode(client_b.b64_private_key), from_hex)
        self.assertEqual(base64.b64decode(client_c.b64_private_key), from_mem)

    # TODO:
    # # MagicMock(side_effect=exceptions.BadRequest)
    # def test_new_from_user_input_throws_with_bad_keys(self):
    #     # Bad hex
    #     # bytes.fromhex will fail, mock it.
    #     self.assertRaises(
    #         exceptions.BadRequest, bnb.new_from_user_input, {"version": "1", "name": "banana", "testnet": True, "private_key": "0xNotHexButBanana"}
    #     )
    #     # Bad mnemonic string
    #     # mnemonic.Mnemonic.to_seed will fail, mock it.
    #     self.assertRaises(
    #         exceptions.BadRequest, bnb.new_from_user_input, {"version": "1", "name": "banana", "testnet": True, "private_key": "Bad Banana Mnemonic"}
    #     )

    # if  user input doesn't include testnet:
    # TODO:
    def test_new_from_user_input_no_testnet_argument(self):
        pass

    # if user includes node_url, but not rpc or api ports, throw BadRequest exception
    # TODO:
    def test_new_from_user_input_no_ports(self):
        pass
        # user_input = {
        #     "version": "1",
        #     "name": "banana",
        #     "node_url": "b.a.n.a.n.a",
        #     "rpc_port": 27147,
        #     "api_port": 1169,
        #     "testnet": True,
        #     "private_key": "SVuyo/Ip6wq7K/caPcpWsx1gwSjf2B6ekH5e7bZ/GaA=",
        # }

        # client = bnb.new_from_at_rest(
        #     {
        #         "version": "1",
        #         "name": "banana",
        #         "node_url": "b.a.n.a.n.a",
        #         "rpc_port": 27147,
        #         "api_port": 1169,
        #         "testnet": True,
        #         "private_key": "SVuyo/Ip6wq7K/caPcpWsx1gwSjf2B6ekH5e7bZ/GaA=",
        #     }
        # )
        # self.assertEqual(client.rpc_port, 27147)
        # self.assertEqual(client.api_port, 1169)

        # self.client.api_port = None
        # FYI: need to make sure this is failing BECAUSE of my specific bad input...
        # self.assertRaises(exceptions.BadRequest, bnb.new_from_user_input, user_input)
        # self.client.rpc_port = None
        # self.assertRaises(exceptions.BadRequest, bnb.new_from_user_input, user_input)

    # if ping fails, throws BadRequest
    # TODO:
    def test_new_from_user_node_ping_fails(self):
        pass

    # TODO:
    def test_ping(self):
        pass

    # DONE:
    def test_get_network_string(self):
        tn = "testnet: Binance-Chain-Nile"
        self.assertEqual(self.client.get_network_string(), f"binance {tn}")

        self.client.testnet = False
        mn = "mainnet: Binance-Chain-Tigris"
        self.assertEqual(self.client.get_network_string(), f"binance {mn}")

    # DONE:
    def test_get_private_key(self):
        b64_private_key = "SVuyo/Ip6wq7K/caPcpWsx1gwSjf2B6ekH5e7bZ/GaA="
        self.assertEqual(self.client.get_private_key(), b64_private_key)
        pass

    # DONE:
    def test_fetch_account_success(self):
        fake_response = requests.Response()
        fake_response._content = b'{"account_number": 12345, "sequence": 0}'
        self.client._call_node_api = MagicMock(return_value=fake_response)
        response = self.client._fetch_account()
        self.assertEqual(response, fake_response.json())
        self.client._call_node_api.assert_called_once_with(f"account/{self.client.address}")

    # TODO:
    def test_fetch_account_failure(self):
        pass

    # DONE:
    def test_build_transaction_msg(self):
        txn_payload = "BANANA_MEMO"
        fake_account = {"account_number": 12345, "sequence": 0}
        self.client._fetch_account = MagicMock(return_value=fake_account)
        inputs = {"address": self.client.address, "coins": [{"amount": 1, "denom": "BNB"}]}
        outputs = {"address": self.client.address, "coins": [{"amount": 1, "denom": "BNB"}]}
        built_txn = {
            "account_number": 12345,
            "sequence": 0,
            "from": self.client.address,
            "memo": "BANANA_MEMO",
            "msgs": [{"type": "cosmos-sdk/Send", "inputs": [inputs], "outputs": [outputs]}],
        }
        test_result = self.client._build_transaction_msg(txn_payload)
        self.assertEqual(test_result, built_txn)
        self.client._fetch_account.assert_called_once()


# kinda low priority
# add testcase to sign_transaction() test, to handle BnbTransaction (only does test right now)
# sign_transaction() also doesn't check for a bad signing that raises BadRequest exception

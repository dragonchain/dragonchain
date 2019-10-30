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
from unittest.mock import MagicMock, patch

from dragonchain import exceptions
from dragonchain import test_env  # noqa: F401
from dragonchain.lib.dto import bnb


class TestBinanceMethods(unittest.TestCase):
    def setUp(self):
        # private_key = "495bb2a3f229eb0abb2bf71a3dca56b31d60c128dfd81e9e907e5eedb67f19a0"
        b64_private_key = "SVuyo/Ip6wq7K/caPcpWsx1gwSjf2B6ekH5e7bZ/GaA="
        self.client = bnb.BinanceNetwork("banana", True, "b.a.n.a.n.a", "rpc_27147", "api_1169", b64_private_key)

    def test_new_from_at_rest_good_input_v1(self):
        client = bnb.new_from_at_rest(
            {
                "version": "1",
                "name": "banana",
                "node_ip": "b.a.n.a.n.a",
                "rpc_port": "rpc_27147",
                "api_port": "api_1169",
                "testnet": True,
                "private_key": "SVuyo/Ip6wq7K/caPcpWsx1gwSjf2B6ekH5e7bZ/GaA=",
            }
        )
        self.assertEqual(client.name, "banana")
        self.assertEqual(client.node_ip, "b.a.n.a.n.a")
        self.assertEqual(client.rpc_port, "rpc_27147")
        self.assertEqual(client.api_port, "api_1169")
        self.assertTrue(client.testnet)
        self.assertEqual(client.wallet.address, "tbnb1u06kxdru0we8at0ktd6q4c5qk80zwdyvhzrulk")

    def test_new_from_at_rest_bad_version(self):
        self.assertRaises(NotImplementedError, bnb.new_from_at_rest, {"version": "1337"})  # good is "1"

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
        self.assertEqual(response, "66616b655f656e636f6465645f74786e")
        mock_encode.assert_called_once()

    def test_publish_transaction(self):
        self.client._build_transaction_msg = MagicMock(return_value={"built_tx": "fake"})  # actual function returns dict
        self.client.sign_transaction = MagicMock(return_value="signed_tx")  # actual function returns hex string
        self._fetch_account = MagicMock(return_value="")
        self.client._call_node_api = MagicMock(return_value="")
        self.client._call_node_rpc = MagicMock(return_value={"result": {"hash": "BOGUS_RESULT_HASH"}})
        response = self.client._publish_transaction("DC-L5:_fake_L5_block_hash")
        self.assertEqual(response, "BOGUS_RESULT_HASH")
        # BROKEN: mocking instance of class as object is not working
        # self.client._call_node_rpc.assert_called_once_with("broadcast_tx_commit", {"tx": "0x" + 'signed_tx'})

    def test_get_current_block(self):
        fake_response = {"result": {"block": {"header": {"height": 12345678}}}}
        self.client._call_node_rpc = MagicMock(return_value=fake_response)
        response = self.client.get_current_block()
        self.assertEqual(response, 12345678)
        self.client._call_node_rpc.assert_called_once_with("block", {})

    def test_check_balance(self):
        fake_response = {"balance": {"free": 1234567890}}
        api_string = "balances/tbnb1u06kxdru0we8at0ktd6q4c5qk80zwdyvhzrulk/BNB"
        self.client._call_node_api = MagicMock(return_value=fake_response)
        response = self.client.check_balance()
        self.assertEqual(response, 1234567890)
        self.client._call_node_api.assert_called_once_with(api_string)

    def test_get_transaction_fee(self):
        fake_response = [{}, {}, {"fixed_fee_params": {"msg_type": "send", "fee": 31337}}, {}, {}]
        self.client._call_node_api = MagicMock(return_value=fake_response)
        response = self.client.get_transaction_fee_estimate()
        self.assertEqual(response, 31337)
        self.client._call_node_api.assert_called_once_with("fees")

    def test_is_transaction_confirmed_final(self):
        self.client.get_current_block = MagicMock(return_value=1245839)  # fake block number
        self.client._call_node_rpc = MagicMock(return_value={"result": {"height": 1245739}})  # txn 100 blocks ago
        response = self.client.is_transaction_confirmed("FakeTxnHash")
        self.assertTrue(response)
        self.client._call_node_rpc.assert_called_once_with("tx", {"hash": "0xFakeTxnHash", "prove": True})
        self.client.get_current_block.assert_called_once()

    def test_is_transaction_confirmed_unconfirmed(self):
        self.client.get_current_block = MagicMock(return_value=1245839)  # fake block number
        self.client._call_node_rpc = MagicMock(return_value={"result": {"height": 1245839}})  # txn in latest block
        response = self.client.is_transaction_confirmed("FakeTxnHash")
        self.assertFalse(response)
        self.client._call_node_rpc.assert_called_once_with("tx", {"hash": "0xFakeTxnHash", "prove": True})
        self.client.get_current_block.assert_called_once()

    def test_is_transaction_confirmed_error(self):
        self.client._call_node_rpc = MagicMock(side_effect=exceptions.InterchainConnectionError)
        self.assertRaises(exceptions.TransactionNotFound, self.client.is_transaction_confirmed, "FakeTxnHash")
        self.client._call_node_rpc.assert_called_once_with("tx", {"hash": "0xFakeTxnHash", "prove": True})

    def test_export_as_at_rest(self):
        self.assertEqual(
            self.client.export_as_at_rest(),
            {
                "version": "1",
                "blockchain": "binance",
                "name": "banana",
                "testnet": True,
                "node_ip": "b.a.n.a.n.a",
                "rpc_port": "rpc_27147",
                "api_port": "api_1169",
                "private_key": "SVuyo/Ip6wq7K/caPcpWsx1gwSjf2B6ekH5e7bZ/GaA=",
            },
        )

    @patch("requests.post", return_value=MagicMock(status_code=200, json=MagicMock(return_value={"result": "MyResult"})))
    def test_rpc_request_success(self, mock_post):
        response = self.client._call_node_rpc("MyMethod", {"symbol": "BANANA"})
        self.assertEqual(response, {"result": "MyResult"})
        mock_post.assert_called_once_with(
            "b.a.n.a.n.a:rpc_27147/", json={"method": "MyMethod", "jsonrpc": "2.0", "params": {"symbol": "BANANA"}, "id": "dontcare"}, timeout=30
        )

    @patch("requests.post", return_value=MagicMock(status_code=200, json=MagicMock(return_value={"error": "MyResult"})))
    def test_rpc_request_error(self, mock_post):
        self.assertRaises(exceptions.InterchainConnectionError, self.client._call_node_rpc, "MyMethod", {"symbol": "BANANA"})
        mock_post.assert_called_once_with(
            "b.a.n.a.n.a:rpc_27147/", json={"method": "MyMethod", "jsonrpc": "2.0", "params": {"symbol": "BANANA"}, "id": "dontcare"}, timeout=30
        )

    @patch("requests.get", return_value=MagicMock(status_code=200, json=MagicMock(return_value={"result": "MyResult"})))
    def test_api_request_success(self, mock_get):
        response = self.client._call_node_api("MyPath")
        self.assertEqual(response, {"result": "MyResult"})
        mock_get.assert_called_once_with("b.a.n.a.n.a:api_1169/api/v1/MyPath", timeout=30)

    @patch("requests.get", return_value=MagicMock(status_code=200, json=MagicMock(return_value={"error": "MyResult"})))
    def test_api_request_error(self, mock_get):
        self.assertRaises(exceptions.InterchainConnectionError, self.client._call_node_api, "MyPath")
        mock_get.assert_called_once_with("b.a.n.a.n.a:api_1169/api/v1/MyPath", timeout=30)

    def test_from_user_input_throws_with_bad_private_key(self):
        fake_input = {
            "version": "1",
            "testnet": True,
            "node_ip": "b.a.n.a.n.a",
            "rpc_port": "rpc_27147",
            "api_port": "api_1169",
            "private_key": "badKey",
        }
        self.assertRaises(exceptions.BadRequest, bnb.new_from_user_input, fake_input)

    @patch("dragonchain.lib.dto.bnb.BinanceNetwork.ping")
    def test_from_user_input_works_with_no_provided_key(self, mock_ping):
        client = bnb.new_from_user_input(
            {"version": "1", "name": "no_private_key", "node_ip": "b.a.n.a.n.a", "rpc_port": "rpc_27147", "api_port": "api_1169", "testnet": True}
        )
        mock_ping.assert_called_once()
        self.assertEqual(client.name, "no_private_key")
        self.assertEqual(client.node_ip, "b.a.n.a.n.a")
        self.assertEqual(client.rpc_port, "rpc_27147")
        self.assertEqual(client.api_port, "api_1169")
        self.assertTrue(client.testnet)

    # BROKEN:
    # def test_new_from_user_input_sets_good_private_keys(self):

    #     # before_body["address"] = "bnb1u06kxdru0we8at0ktd6q4c5qk80zwdyveh2cl8"
    #     # priv_key = "495bb2a3f229eb0abb2bf71a3dca56b31d60c128dfd81e9e907e5eedb67f19a0"
    #     # base64.b64encode(binascii.unhexlify(self.wallet.private_key)).decode("ascii")

    #     # binascii.unhexlify(self.wallet.private_key)

    #     # Good hex key without 0x
    #     client_a = bnb.new_from_user_input(
    #         {"version": "1", "name": "banana", "testnet": True, "private_key": "7796b9ac433fab2a83d281e8064f29c935133139b62ec52c8e73de28440c0dc6"}
    #     )

    #     # Good hex key with 0x
    #     client_b = bnb.new_from_user_input(
    #         {"version": "1", "name": "banana", "testnet": True, "private_key": "0x7796b9ac433fab2a83d281e8064f29c935133139b62ec52c8e73de28440c0dc6"}
    #     )
    #     # Good base64 key
    #     client_c = bnb.new_from_user_input(
    #         {"version": "1", "name": "banana", "testnet": True, "private_key": "d5a5rEM/qyqD0oHoBk8pyTUTMTm2LsUsjnPeKEQMDcY="}
    #     )
    #     print(client_b.wallet.private_key.to_bytes)
    #     print("poop")
    #     print(client_b.wallet.private_key)

    #     self.assertEqual(
    #         client_a.wallet.private_key.to_bytes(), b"w\x96\xb9\xacC?\xab*\x83\xd2\x81\xe8\x06O)\xc95\x1319\xb6.\xc5,\x8es\xde(D\x0c\r\xc6"
    #     )
    #     self.assertEqual(
    #         client_b.wallet.private_key.to_bytes(), b"w\x96\xb9\xacC?\xab*\x83\xd2\x81\xe8\x06O)\xc95\x1319\xb6.\xc5,\x8es\xde(D\x0c\r\xc6"
    #     )
    #     self.assertEqual(
    #         client_c.wallet.private_key.to_bytes(), b"w\x96\xb9\xacC?\xab*\x83\xd2\x81\xe8\x06O)\xc95\x1319\xb6.\xc5,\x8es\xde(D\x0c\r\xc6"
    #     )

    def test_new_from_user_input_throws_with_bad_keys(self):
        # Bad hex
        self.assertRaises(
            exceptions.BadRequest, bnb.new_from_user_input, {"version": "1", "name": "banana", "testnet": True, "private_key": "0xNotHexButBanana"}
        )
        # Bad base64
        self.assertRaises(
            exceptions.BadRequest,
            bnb.new_from_user_input,
            {"version": "1", "name": "banana", "testnet": True, "private_key": "BadPrivateKeyNoBanana="},
        )

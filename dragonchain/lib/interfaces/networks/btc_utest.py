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
from dragonchain.lib.interfaces.networks import btc


class TestBitcoinMethods(unittest.TestCase):
    @patch("dragonchain.lib.interfaces.networks.btc.secrets.get_dc_secret", return_value="KhDH0BKv7n9iFwMc2ClTwJ5zb3R2fTLuQEupXSgoYxo=")
    def setUp(self, mock_get_secret):
        self.client = btc.BTCClient("BTC_TESTNET3")
        mock_get_secret.assert_called_once_with("btc-testnet3-private-key")

    @patch("dragonchain.lib.interfaces.networks.btc.BTCClient.call", return_value="MyFakeTransactionHash")
    @patch("dragonchain.lib.interfaces.networks.btc.BTCClient._create_raw_transaction", return_value={"nonce": "0x0"})
    @patch("dragonchain.lib.interfaces.networks.btc.BTCClient.sign_transaction", return_value="signed_transaction")
    def test_publish_creates_signs_and_sends(self, mock_sign, mock_create, mock_call):
        response = self.client.publish_transaction("DC-L5:0xhash")
        self.assertEqual(response, "MyFakeTransactionHash")

        mock_call.assert_called_once_with("sendrawtransaction", "signed_transaction")
        mock_sign.assert_called_once_with({"nonce": "0x0"})
        mock_create.assert_called_once_with("DC-L5:0xhash")

    @patch("dragonchain.lib.interfaces.networks.btc.BTCClient._get_utxos", return_value=[])
    def test_sign_transaction(self, mock_get_utxos):
        self.client.private_key.create_transaction = MagicMock()
        self.client.private_key.sign_transaction = MagicMock(return_value="signature")
        fake_transaction = {"fee": 15, "data": "hello world"}
        self.assertEqual("signature", self.client.sign_transaction(fake_transaction))

    @patch("dragonchain.lib.interfaces.networks.btc.BTCClient.call", return_value=1538271)
    def test_get_current_block_calls_rpc(self, mock_call):
        response = self.client.get_current_block()
        self.assertEqual(response, 1538271)

        mock_call.assert_called_once_with("getblockcount")

    def test_get_retry_threshold(self):
        response = self.client.get_retry_threshold()
        self.assertEqual(response, 10)

    @patch("dragonchain.lib.interfaces.networks.btc.BTCClient.call", return_value=1.543543)
    def test_check_address_balance(self, mock_call):
        response = self.client.check_address_balance()
        self.assertEqual(response, int(1.543543 * 100000000))

        mock_call.assert_called_once_with("getreceivedbyaddress", "mzhqDGPpFVxDUhYiDgrdUpzGw4NFBkXPaK", 6)

    @patch("dragonchain.lib.interfaces.networks.btc.BTCClient._calculate_transaction_fee", return_value=20)
    def test_get_transaction_fee_estimate(self, mock_calculate_fee):
        response = self.client.get_transaction_fee_estimate()
        self.assertEqual(response, 262 * 20)
        mock_calculate_fee.assert_called_once()

    def test_btc_to_satoshi(self):
        self.assertEqual(self.client.btc_to_satoshi(1), 100000000)
        self.assertEqual(self.client.btc_to_satoshi(1.15325), 115325000)
        self.assertEqual(self.client.btc_to_satoshi(0.4564), 45640000)

    @patch("dragonchain.lib.interfaces.networks.btc.BTCClient.call", return_value={"feerate": 1e-05})
    def test_calculate_transaction_fee_rounds_up(self, mock_call):
        # Client was initialized with eth, no need to change network variable
        response = self.client._calculate_transaction_fee()
        self.assertEqual(response, 10)
        mock_call.assert_called_once_with("estimatesmartfee", 2)

    @patch("dragonchain.lib.interfaces.networks.btc.BTCClient.call", return_value={"feerate": 1.05e-04})
    def test_calculate_transaction_fee(self, mock_call):
        response = self.client._calculate_transaction_fee()
        self.assertEqual(response, 11)
        mock_call.assert_called_once_with("estimatesmartfee", 2)

    def test_create_raw_transaction(self):
        response = self.client._create_raw_transaction("DC-L5:0xFakeHash")
        self.assertEqual(response, {"data": "44432d4c353a307846616b6548617368"})

    def test_get_network_returns_correct_network_prod(self):
        self.client.network = "BTC_MAINNET"
        self.assertEqual(self.client._get_network(), btc.Networks.Mainnet.value)

    def test_get_network_returns_correct_network_dev(self):
        self.client.network = "BTC_TESTNET3"
        self.assertEqual(self.client._get_network(), btc.Networks.Testnet.value)

    @patch("dragonchain.lib.interfaces.networks.btc.BTCClient.call", return_value={"confirmations": 7})
    def test_is_transaction_confirmed_final(self, mock_call):
        response = self.client.is_transaction_confirmed("0xFakeHash")
        self.assertTrue(response)

        mock_call.assert_called_once_with("getrawtransaction", "0xFakeHash", True)

    @patch("dragonchain.lib.interfaces.networks.btc.BTCClient.call", side_effect=RuntimeError)
    def test_is_transaction_confirmed_error(self, mock_call):
        response = self.client.is_transaction_confirmed("0xFakeHash")
        self.assertEqual(response, "0xFakeHash")

        mock_call.assert_called_once_with("getrawtransaction", "0xFakeHash", True)

    @patch("dragonchain.lib.interfaces.networks.btc.BTCClient.call", return_value={"Pending": "Block"})
    def test_is_transaction_confirmed_pending(self, mock_call):
        response = self.client.is_transaction_confirmed("0xFakeHash")
        self.assertFalse(response)

        mock_call.assert_called_once_with("getrawtransaction", "0xFakeHash", True)

    @patch("dragonchain.lib.interfaces.networks.btc.requests.post", return_value=MagicMock(json=MagicMock(return_value={"result": "MyResult"})))
    def test_rpc_request_success(self, mock_post):
        self.client.endpoint = "http://dragonchain.com:4738"
        self.client.auth = "dGVzdDp0ZXN0"
        response = self.client.call("myMethod", "arg1", 2, True)

        self.assertEqual(response, "MyResult")
        mock_post.assert_called_once_with(
            "http://dragonchain.com:4738",
            json={"method": "myMethod", "params": ["arg1", 2, True], "id": 1},
            headers={"Authorization": "Basic dGVzdDp0ZXN0"},
            timeout=30,
        )

    @patch("dragonchain.lib.interfaces.networks.btc.requests.post", return_value=MagicMock(json=MagicMock(return_value={"error": "MyResult"})))
    def test_rpc_request_error(self, mock_post):
        self.client.endpoint = "http://dragonchain.com:4738"
        self.client.auth = "dGVzdDp0ZXN0"
        self.assertRaises(exceptions.RPCError, self.client.call, "myMethod", "arg1", 2, True)

        mock_post.assert_called_once_with(
            "http://dragonchain.com:4738",
            json={"method": "myMethod", "params": ["arg1", 2, True], "id": 1},
            headers={"Authorization": "Basic dGVzdDp0ZXN0"},
            timeout=30,
        )

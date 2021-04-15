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
from unittest.mock import patch, MagicMock, call

from dragonchain import test_env  # noqa: F401
from dragonchain import exceptions
from dragonchain.lib.dto import btc


class TestBitcoinMethods(unittest.TestCase):
    def setUp(self):
        self.client = btc.BitcoinNetwork("banana", "http://whatever", True, "KhDH0BKv7n9iFwMc2ClTwJ5zb3R2fTLuQEupXSgoYxo=", "auth")

    def test_new_from_at_rest_good_input_v1(self):
        client = btc.new_from_at_rest(
            {
                "version": "1",
                "name": "banana",
                "rpc_address": "http://yeah",
                "testnet": True,
                "private_key": "KhDH0BKv7n9iFwMc2ClTwJ5zb3R2fTLuQEupXSgoYxo=",
                "authorization": None,
            }
        )
        self.assertEqual(client.name, "banana")
        self.assertEqual(client.rpc_address, "http://yeah")
        self.assertTrue(client.testnet)
        self.assertEqual(client.priv_key.address, "mzhqDGPpFVxDUhYiDgrdUpzGw4NFBkXPaK")
        self.assertIsNone(client.authorization)

    def test_new_from_at_rest_bad_version(self):
        self.assertRaises(NotImplementedError, btc.new_from_at_rest, {"version": "9999999"})

    def test_should_retry_broadcast_true(self):
        self.client.get_current_block = MagicMock(return_value=100)
        self.assertTrue(self.client.should_retry_broadcast(1))
        self.client.get_current_block.assert_called_once()

    def test_should_retry_broadcast_false(self):
        self.client.get_current_block = MagicMock(return_value=100)
        self.assertFalse(self.client.should_retry_broadcast(99))
        self.client.get_current_block.assert_called_once()

    def test_publish_creates_signs_and_sends(self):
        self.client._call = MagicMock(return_value="MyFakeTransactionHash")
        self.client.sign_transaction = MagicMock(return_value="signed_transaction")
        response = self.client._publish_transaction("DC-L5:0xhash")
        self.assertEqual(response, "MyFakeTransactionHash")

        self.client._call.assert_called_once_with("sendrawtransaction", "signed_transaction")
        self.client.sign_transaction.assert_called_once_with({"data": "DC-L5:0xhash"})

    def test_sign_transaction(self):
        self.client._get_utxos = MagicMock(return_value=[])
        self.client.priv_key.create_transaction = MagicMock()
        self.client.priv_key.sign_transaction = MagicMock(return_value="signature")
        fake_transaction = {"fee": 15, "data": "hello world"}
        self.assertEqual("signature", self.client.sign_transaction(fake_transaction))

    def test_get_current_block_calls_rpc(self):
        self.client._call = MagicMock(return_value=1538271)
        response = self.client.get_current_block()
        self.assertEqual(response, 1538271)

        self.client._call.assert_called_once_with("getblockcount")

    def test_check_balance(self):
        self.client._call = MagicMock(return_value=1.543543)
        response = self.client.check_balance()
        self.assertEqual(response, 154354300)
        self.client._call.assert_called_once_with("getreceivedbyaddress", "mzhqDGPpFVxDUhYiDgrdUpzGw4NFBkXPaK", 6)

    def test_get_transaction_fee_estimate(self):
        self.client._calculate_transaction_fee = MagicMock(return_value=20)
        response = self.client.get_transaction_fee_estimate()
        self.assertEqual(response, 5240)
        self.client._calculate_transaction_fee.assert_called_once()

    def test_btc_to_satoshi(self):
        self.assertEqual(btc.btc_to_satoshi(1), 100000000)
        self.assertEqual(btc.btc_to_satoshi(1.15325), 115325000)
        self.assertEqual(btc.btc_to_satoshi(0.4564), 45640000)

    def test_calculate_transaction_fee_rounds_up(self):
        self.client._call = MagicMock(return_value={"feerate": 1e-05})
        # Client was initialized with eth, no need to change network variable
        response = self.client._calculate_transaction_fee()
        self.assertEqual(response, 10)
        self.client._call.assert_called_once_with("estimatesmartfee", 2)

    def test_calculate_transaction_fee(self):
        self.client._call = MagicMock(return_value={"feerate": 1.05e-04})
        response = self.client._calculate_transaction_fee()
        self.assertEqual(response, 11)
        self.client._call.assert_called_once_with("estimatesmartfee", 2)

    def test_is_transaction_confirmed_final(self):
        self.client._call = MagicMock(return_value={"confirmations": 7})
        response = self.client.is_transaction_confirmed("0xFakeHash")
        self.assertTrue(response)
        self.client._call.assert_called_once_with("getrawtransaction", "0xFakeHash", True)

    def test_is_transaction_confirmed_error(self):
        self.client._call = MagicMock(side_effect=exceptions.InterchainConnectionError)
        self.assertRaises(exceptions.TransactionNotFound, self.client.is_transaction_confirmed, "0xFakeHash")
        self.client._call.assert_called_once_with("getrawtransaction", "0xFakeHash", True)

    def test_is_transaction_confirmed_pending(self):
        self.client._call = MagicMock(return_value={"Pending": "Block"})
        response = self.client.is_transaction_confirmed("0xFakeHash")
        self.assertFalse(response)
        self.client._call.assert_called_once_with("getrawtransaction", "0xFakeHash", True)

    def test_register_address_raises(self):
        self.client._call = MagicMock(return_value=["nothere"])
        self.assertRaises(exceptions.AddressRegistrationFailure, self.client.register_address)
        self.client._call.assert_has_calls(
            [call("listlabels"), call("importaddress", "mzhqDGPpFVxDUhYiDgrdUpzGw4NFBkXPaK", "mzhqDGPpFVxDUhYiDgrdUpzGw4NFBkXPaK", False)]
        )

    def test_register_address_skips_already_registered(self):
        self.client._call = MagicMock(return_value=["mzhqDGPpFVxDUhYiDgrdUpzGw4NFBkXPaK"])
        self.client.register_address()
        self.client._call.assert_called_once_with("listlabels")

    def test_export_as_at_rest(self):
        self.assertEqual(
            self.client.export_as_at_rest(),
            {
                "version": "1",
                "blockchain": "bitcoin",
                "name": "banana",
                "rpc_address": "http://whatever",
                "authorization": "auth",
                "testnet": True,
                "private_key": "KhDH0BKv7n9iFwMc2ClTwJ5zb3R2fTLuQEupXSgoYxo=",
            },
        )

    @patch("requests.post", return_value=MagicMock(status_code=200, json=MagicMock(return_value={"result": "MyResult"})))
    def test_rpc_request_success(self, mock_post):
        response = self.client._call("myMethod", "arg1", 2, True)
        self.assertEqual(response, "MyResult")
        mock_post.assert_called_once_with(
            "http://whatever",
            json={"method": "myMethod", "params": ["arg1", 2, True], "id": "1", "jsonrpc": "1.0"},
            headers={"Authorization": "Basic auth", "Content-Type": "text/plain"},
            timeout=20,
        )

    @patch("requests.post", return_value=MagicMock(status_code=200, json=MagicMock(return_value={"error": "MyResult"})))
    def test_rpc_request_error(self, mock_post):
        self.assertRaises(exceptions.InterchainConnectionError, self.client._call, "myMethod", "arg1", 2, True)
        mock_post.assert_called_once_with(
            "http://whatever",
            json={"method": "myMethod", "params": ["arg1", 2, True], "id": "1", "jsonrpc": "1.0"},
            headers={"Authorization": "Basic auth", "Content-Type": "text/plain"},
            timeout=20,
        )

    @patch("dragonchain.lib.dto.btc.BitcoinNetwork.ping")
    @patch("dragonchain.lib.dto.btc.BitcoinNetwork.register_address")
    def test_from_user_input_wif_defaults(self, mock_register, mock_ping):
        client = btc.new_from_user_input({"version": "1", "name": "banana", "private_key": "L1EB9j5D3PN3dZFoKKczBy9ieav5cx2dAWASBHmhS9Yn7Go5U4dh"})
        mock_ping.assert_called_once()
        mock_register.assert_called_once_with(False)
        self.assertEqual(client.name, "banana")
        self.assertEqual(client.rpc_address, "http://internal-Btc-Mainnet-Internal-297595751.us-west-2.elb.amazonaws.com:8332")
        self.assertEqual(client.authorization, "Yml0Y29pbnJwYzpkcmFnb24=")
        self.assertEqual(client.priv_key.to_bytes(), b"w\x96\xb9\xacC?\xab*\x83\xd2\x81\xe8\x06O)\xc95\x1319\xb6.\xc5,\x8es\xde(D\x0c\r\xc6")
        self.assertFalse(client.testnet)

    def test_from_user_input_wif_throws_with_mismatching_testnet(self):
        self.assertRaises(
            exceptions.BadRequest,
            btc.new_from_user_input,
            {"version": "1", "name": "banana", "testnet": True, "private_key": "L1EB9j5D3PN3dZFoKKczBy9ieav5cx2dAWASBHmhS9Yn7Go5U4dh"},
        )

    def test_from_user_input_requires_testnet_with_b64_key(self):
        self.assertRaises(
            exceptions.BadRequest,
            btc.new_from_user_input,
            {"version": "1", "name": "banana", "private_key": "d5a5rEM/qyqD0oHoBk8pyTUTMTm2LsUsjnPeKEQMDcY="},
        )

    @patch("dragonchain.lib.dto.btc.BitcoinNetwork.ping")
    @patch("dragonchain.lib.dto.btc.BitcoinNetwork.register_address")
    def test_from_user_input_works_with_no_provided_key(self, mock_register, mock_ping):
        client = btc.new_from_user_input({"version": "1", "name": "nokey", "testnet": True})
        mock_ping.assert_called_once()
        mock_register.assert_called_once_with(False)
        self.assertEqual(client.name, "nokey")
        self.assertEqual(client.rpc_address, "http://internal-Btc-Testnet-Internal-1334656512.us-west-2.elb.amazonaws.com:18332")
        self.assertEqual(client.authorization, "Yml0Y29pbnJwYzpkcmFnb24=")
        self.assertTrue(bool(client.priv_key.to_bytes()))
        self.assertTrue(client.testnet)

    def test_from_user_input_throws_bad_version(self):
        self.assertRaises(exceptions.BadRequest, btc.new_from_user_input, {"version": "99999"})

    @patch("dragonchain.lib.dto.btc.BitcoinNetwork.ping", side_effect=RuntimeError)
    def test_from_user_input_throws_if_node_not_accessible(self, mock_ping):
        self.assertRaises(exceptions.BadRequest, btc.new_from_user_input, {"version": "1", "name": "nokey", "testnet": True})

    @patch("dragonchain.lib.dto.btc.BitcoinNetwork.ping")
    @patch("dragonchain.lib.dto.btc.BitcoinNetwork.register_address")
    def test_from_user_input_uses_provided_node_and_auth(self, mock_register, mock_ping):
        client = btc.new_from_user_input({"version": "1", "name": "nokey", "testnet": True, "rpc_address": "thing", "rpc_authorization": "yup"})
        self.assertEqual(client.rpc_address, "thing")
        self.assertEqual(client.authorization, "yup")

    @patch("dragonchain.lib.dto.btc.BitcoinNetwork.ping")
    @patch("dragonchain.lib.dto.btc.BitcoinNetwork.register_address")
    def test_from_user_input_scans_if_requested(self, mock_register, mock_ping):
        btc.new_from_user_input(
            {"version": "1", "name": "nokey", "testnet": True, "private_key": "d5a5rEM/qyqD0oHoBk8pyTUTMTm2LsUsjnPeKEQMDcY=", "utxo_scan": True}
        )
        mock_register.assert_called_once_with(True)

    def test_from_user_input_throws_with_bad_private_key(self):
        self.assertRaises(exceptions.BadRequest, btc.new_from_user_input, {"version": "1", "name": "nokey", "testnet": True, "private_key": "badKey"})

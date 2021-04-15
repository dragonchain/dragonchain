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
from unittest.mock import MagicMock, patch

import web3

from dragonchain import exceptions
from dragonchain import test_env  # noqa: F401
from dragonchain.lib.dto import eth


class TestEthereumMethods(unittest.TestCase):
    def setUp(self):
        self.client = eth.EthereumNetwork("banana", "http://whatever", 3, "KhDH0BKv7n9iFwMc2ClTwJ5zb3R2fTLuQEupXSgoYxo=")

    def test_new_from_at_rest_good_input_v1(self):
        client = eth.new_from_at_rest(
            {
                "version": "1",
                "name": "banana",
                "rpc_address": "http://yeah",
                "chain_id": 3,
                "private_key": "KhDH0BKv7n9iFwMc2ClTwJ5zb3R2fTLuQEupXSgoYxo=",
            }
        )
        self.assertEqual(client.name, "banana")
        self.assertEqual(client.rpc_address, "http://yeah")
        self.assertEqual(client.chain_id, 3)
        self.assertEqual(client.address, "0xe49E4BDA371C97ac89332bCd1281d1Bc17D55955")

    def test_new_from_at_rest_bad_version(self):
        self.assertRaises(NotImplementedError, eth.new_from_at_rest, {"version": "9999999"})

    def test_publish_creates_signs_and_sends(self):
        self.client.sign_transaction = MagicMock(return_value="signed_transaction")
        self.client.w3.eth.getTransactionCount = MagicMock(return_value=0)
        self.client.w3.eth.sendRawTransaction = MagicMock(
            return_value=b"\xec>s;\xb6\x8a\xbb?\xfa\x87\xa1+\x03\x9at\x9f\xcc\xafXDn\xee\xed\xa9:\xd0\xd5\x9fQ\x03\x8f\xf2"
        )

        response = self.client._publish_transaction("DC-L5:0xhash")
        self.assertEqual(response, "0xec3e733bb68abb3ffa87a12b039a749fccaf58446eeeeda93ad0d59f51038ff2")

        self.client.sign_transaction.assert_called_once_with(
            {"to": "0x0000000000000000000000000000000000000000", "value": "0x0", "data": "0x44432d4c353a307868617368"}
        )
        self.client.w3.eth.sendRawTransaction.assert_called_once_with("signed_transaction")

    def test_get_current_block_calls_web3(self):
        self.client.w3.eth.getBlock = MagicMock(return_value={"number": 1538271})
        response = self.client.get_current_block()
        self.assertEqual(response, 1538271)
        self.client.w3.eth.getBlock.assert_called_once_with("latest")

    def test_should_retry_broadcast_true(self):
        self.client.get_current_block = MagicMock(return_value=100)
        self.assertTrue(self.client.should_retry_broadcast(1))
        self.client.get_current_block.assert_called_once()

    def test_should_retry_broadcast_false(self):
        self.client.get_current_block = MagicMock(return_value=100)
        self.assertFalse(self.client.should_retry_broadcast(99))
        self.client.get_current_block.assert_called_once()

    def test_check_balance(self):
        self.client.w3.eth.getBalance = MagicMock(return_value=99241288782895)
        response = self.client.check_balance()
        self.assertEqual(response, 99241288782895)
        self.client.w3.eth.getBalance.assert_called_once_with("0xe49E4BDA371C97ac89332bCd1281d1Bc17D55955")

    def test_get_transaction_fee_estimate(self):
        self.client._calculate_transaction_fee = MagicMock(return_value=14000000000)
        response = self.client.get_transaction_fee_estimate()
        self.assertEqual(response, 840000000000000)
        self.client._calculate_transaction_fee.assert_called_once()

    def test_calculate_transaction_fee_for_eth(self):
        self.client.w3.eth.generateGasPrice = MagicMock(return_value=14000000000)
        response = self.client._calculate_transaction_fee()
        self.assertEqual(response, 14000000000)
        self.client.w3.eth.generateGasPrice.assert_called_once()

    def test_sign_transaction(self):
        mock_signed_transaction = MagicMock()
        mock_signed_transaction.rawTransaction.hex.return_value = "signature"
        self.client.w3.eth.account.sign_transaction = MagicMock(return_value=mock_signed_transaction)
        fake_transaction = {
            "nonce": "0x0",
            "value": "0x0",
            "to": "0x0000000000000000000000000000000000000000",
            "gas": "0xC3502",
            "gasPrice": "0xB2D05E00",
        }
        self.client.sign_transaction(fake_transaction)
        mock_signed_transaction.rawTransaction.hex.assert_called_once()
        self.assertEqual("signature", self.client.sign_transaction(fake_transaction))

    def test_is_transaction_confirmed_final(self):
        self.client.get_current_block = MagicMock(return_value=1245839)
        self.client.w3.eth.getTransaction = MagicMock(return_value={"blockNumber": 1245739})
        response = self.client.is_transaction_confirmed("0xFakeHash")
        self.assertTrue(response)
        self.client.w3.eth.getTransaction.assert_called_once_with("0xFakeHash")
        self.client.get_current_block.assert_called_once()

    def test_is_transaction_confirmed_unconfirmed(self):
        self.client.get_current_block = MagicMock(return_value=1245839)
        self.client.w3.eth.getTransaction = MagicMock(return_value={"blockNumber": 1245837})
        response = self.client.is_transaction_confirmed("0xFakeHash")
        self.assertFalse(response)
        self.client.w3.eth.getTransaction.assert_called_once_with("0xFakeHash")
        self.client.get_current_block.assert_called_once()

    def test_is_transaction_confirmed_pending(self):
        self.client.get_current_block = MagicMock(return_value=1245839)
        self.client.w3.eth.getTransaction = MagicMock(return_value={"blockNumber": None})
        response = self.client.is_transaction_confirmed("0xFakeHash")
        self.assertFalse(response)
        self.client.w3.eth.getTransaction.assert_called_once_with("0xFakeHash")
        self.client.get_current_block.assert_called_once()

    def test_is_transaction_confirmed_dropped(self):
        self.client.w3.eth.getTransaction = MagicMock(side_effect=web3.exceptions.TransactionNotFound)
        self.assertRaises(exceptions.TransactionNotFound, self.client.is_transaction_confirmed, "0xBanana")
        self.client.w3.eth.getTransaction.assert_called_once_with("0xBanana")

    def test_export_as_at_rest(self):
        self.assertEqual(
            self.client.export_as_at_rest(),
            {
                "version": "1",
                "blockchain": "ethereum",
                "name": "banana",
                "rpc_address": "http://whatever",
                "chain_id": 3,
                "private_key": "KhDH0BKv7n9iFwMc2ClTwJ5zb3R2fTLuQEupXSgoYxo=",
            },
        )

    @patch("dragonchain.lib.dto.eth.EthereumNetwork.check_rpc_chain_id", return_value=1)
    def test_new_from_user_input_defaults(self, mock_check_chain_id):
        client = eth.new_from_user_input({"version": "1", "name": "banana", "chain_id": 1})
        self.assertEqual(client.chain_id, 1)
        self.assertTrue(bool(client.address))  # Ensure we got an address (private key was generated for us)
        self.assertEqual(client.rpc_address, "https://mainnet.infura.io/v3/86c6d074149d49f5b7cddb8d340b862a")
        mock_check_chain_id.return_value = 3
        client = eth.new_from_user_input({"version": "1", "name": "banana", "chain_id": 3})
        self.assertEqual(client.rpc_address, "http://internal-Parity-Ropsten-Internal-1699752391.us-west-2.elb.amazonaws.com:8545")
        mock_check_chain_id.return_value = 1
        client = eth.new_from_user_input({"version": "1", "name": "banana", "chain_id": 61})
        self.assertEqual(client.rpc_address, "http://internal-Parity-Classic-Internal-2003699904.us-west-2.elb.amazonaws.com:8545")
        self.assertEqual(client.chain_id, 61)  # Ensure the chain id for ETC mainnet is correct

    @patch("dragonchain.lib.dto.eth.EthereumNetwork.check_rpc_chain_id", return_value=1)
    def test_new_from_user_input_sets_good_private_keys(self, mock_check_chain_id):
        # Good hex key without 0x
        clienta = eth.new_from_user_input(
            {"version": "1", "name": "banana", "chain_id": 1, "private_key": "7796b9ac433fab2a83d281e8064f29c935133139b62ec52c8e73de28440c0dc6"}
        )
        # Good hex key with 0x
        clientb = eth.new_from_user_input(
            {"version": "1", "name": "banana", "chain_id": 1, "private_key": "0x7796b9ac433fab2a83d281e8064f29c935133139b62ec52c8e73de28440c0dc6"}
        )
        # Good base64 key
        clientc = eth.new_from_user_input(
            {"version": "1", "name": "banana", "chain_id": 1, "private_key": "d5a5rEM/qyqD0oHoBk8pyTUTMTm2LsUsjnPeKEQMDcY="}
        )
        self.assertEqual(clienta.priv_key.to_bytes(), b"w\x96\xb9\xacC?\xab*\x83\xd2\x81\xe8\x06O)\xc95\x1319\xb6.\xc5,\x8es\xde(D\x0c\r\xc6")
        self.assertEqual(clientb.priv_key.to_bytes(), b"w\x96\xb9\xacC?\xab*\x83\xd2\x81\xe8\x06O)\xc95\x1319\xb6.\xc5,\x8es\xde(D\x0c\r\xc6")
        self.assertEqual(clientc.priv_key.to_bytes(), b"w\x96\xb9\xacC?\xab*\x83\xd2\x81\xe8\x06O)\xc95\x1319\xb6.\xc5,\x8es\xde(D\x0c\r\xc6")

    def test_new_from_user_input_throws_with_bad_keys(self):
        # Bad hex
        self.assertRaises(
            exceptions.BadRequest,
            eth.new_from_user_input,
            {"version": "1", "name": "banana", "chain_id": 1, "private_key": "0xnothexnothexab2a83d281e8064f29c935133139b62ec52c8e73de28440c0dc6"},
        )
        # Bad base64
        self.assertRaises(
            exceptions.BadRequest,
            eth.new_from_user_input,
            {"version": "1", "name": "banana", "chain_id": 1, "private_key": "badrEM/qyqD0oHoBk8pyTUTMTm2LsUsjnPeKEQMDcY="},
        )

    def test_new_from_user_inputs_throws_with_no_rpc_and_bad_chain_id(self):
        # No rpc or chain id
        self.assertRaises(exceptions.BadRequest, eth.new_from_user_input, {"version": "1", "name": "banana"})
        # No rpc and bad chain id
        self.assertRaises(exceptions.BadRequest, eth.new_from_user_input, {"version": "1", "name": "banana", "chain_id": 999})

    @patch("dragonchain.lib.dto.eth.EthereumNetwork.check_rpc_chain_id", return_value=1)
    def test_new_from_user_input_throws_with_mismatching_chain_id(self, mock_check_chain_id):
        self.assertRaises(exceptions.BadRequest, eth.new_from_user_input, {"version": "1", "name": "banana", "rpc_address": "hi", "chain_id": 999})

    @patch("dragonchain.lib.dto.eth.EthereumNetwork.check_rpc_chain_id", side_effect=RuntimeError)
    def test_new_from_user_input_throws_with_inaccessable_rpc(self, mock_check_chain_id):
        self.assertRaises(exceptions.BadRequest, eth.new_from_user_input, {"version": "1", "name": "banana", "rpc_address": "hi", "chain_id": 999})

    def test_new_from_user_input_throws_with_bad_version(self):
        self.assertRaises(exceptions.BadRequest, eth.new_from_user_input, {"version": "999"})

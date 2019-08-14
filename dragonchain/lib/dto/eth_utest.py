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
from dragonchain.lib.dto import eth


class TestEthereumMethods(unittest.TestCase):
    @patch("dragonchain.lib.interfaces.networks.eth.secrets.get_dc_secret", return_value="KhDH0BKv7n9iFwMc2ClTwJ5zb3R2fTLuQEupXSgoYxo=")
    def setUp(self, mock_get_secret):
        self.client = eth.ETHClient("ETH_ROPSTEN")
        mock_get_secret.assert_called_once_with("eth-ropsten-private-key")

    @patch("dragonchain.lib.interfaces.networks.eth.ETHClient._create_raw_transaction", return_value={"nonce": "0x0"})
    @patch("dragonchain.lib.interfaces.networks.eth.ETHClient.sign_transaction", return_value="signed_transaction")
    def test_publish_creates_signs_and_sends(self, mock_sign, mock_create):
        self.client.w3.eth.sendRawTransaction = MagicMock(
            return_value=b"\xec>s;\xb6\x8a\xbb?\xfa\x87\xa1+\x03\x9at\x9f\xcc\xafXDn\xee\xed\xa9:\xd0\xd5\x9fQ\x03\x8f\xf2"
        )

        response = self.client.publish_transaction("DC-L5:0xhash")
        self.assertEqual(response, "0xec3e733bb68abb3ffa87a12b039a749fccaf58446eeeeda93ad0d59f51038ff2")

        self.client.w3.eth.sendRawTransaction.assert_called_once_with("signed_transaction")
        mock_sign.assert_called_once_with({"nonce": "0x0"})
        mock_create.assert_called_once_with("DC-L5:0xhash")

    def test_get_current_block_calls_web3(self):
        self.client.w3.eth.getBlock = MagicMock(return_value={"number": 1538271})

        response = self.client.get_current_block()
        self.assertEqual(response, 1538271)

        self.client.w3.eth.getBlock.assert_called_once_with("latest")

    def test_get_retry_threshold(self):
        response = self.client.get_retry_threshold()
        self.assertEqual(response, 30)

    def test_check_balance(self):
        self.client.w3.eth.getBalance = MagicMock(return_value=99241288782895)

        response = self.client.check_balance()
        self.assertEqual(response, 99241288782895)

        self.client.w3.eth.getBalance.assert_called_once_with("0xe49E4BDA371C97ac89332bCd1281d1Bc17D55955")

    @patch("dragonchain.lib.interfaces.networks.eth.ETHClient._calculate_transaction_fee", return_value=(14000000000, 60000))
    def test_get_transaction_fee_estimate(self, mock_calculate_fee):
        response = self.client.get_transaction_fee_estimate()
        self.assertEqual(response, 14000000000 * 60000)
        mock_calculate_fee.assert_called_once()

    def test_calculate_transaction_fee_for_eth(self):
        # Client was initialized with eth, no need to change network variable
        self.client.w3.eth.generateGasPrice = MagicMock(return_value=14000000000)

        response = self.client._calculate_transaction_fee()
        self.assertEqual(response, (14000000000, 60000))

        self.client.w3.eth.generateGasPrice.assert_called_once()

    def test_calculate_transaction_fee_for_etc(self):
        # Client was initialized with eth, need to change network variable
        self.client.network = "etc"
        self.client.w3.eth.generateGasPrice = MagicMock(return_value=14000000000)

        response = self.client._calculate_transaction_fee()
        self.assertEqual(response, (30000000000, 60000))

        self.client.w3.eth.generateGasPrice.assert_not_called()

    def test_sign_transaction(self):
        mock_signed_transaction = MagicMock()
        mock_signed_transaction.rawTransaction.hex = MagicMock(return_value="signature")
        self.client.w3.eth.account.signTransaction = MagicMock(return_value=mock_signed_transaction)
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

    def test_create_raw_transaction(self):
        self.client.w3.eth.getTransactionCount = MagicMock(return_value=0)

        response = self.client._create_raw_transaction("DC-L5:0xFakeHash")
        self.assertEqual(
            response,
            {
                "nonce": "0x0",
                "to": "0x0000000000000000000000000000000000000000",
                "from": "0xe49E4BDA371C97ac89332bCd1281d1Bc17D55955",
                "value": "0x0",
                "data": "0x44432d4c353a307846616b6548617368",
            },
        )

        self.client.w3.eth.getTransactionCount.assert_called_once_with("0xe49E4BDA371C97ac89332bCd1281d1Bc17D55955")

    @patch("dragonchain.lib.interfaces.networks.eth.web3.HTTPProvider")
    def test_get_provider_returns_correct_network_prod_eth(self, mock_provider):
        self.client.network = "ETH_MAINNET"
        self.client._get_provider()
        mock_provider.assert_called_once_with(eth.Networks.Mainnet.value)

    @patch("dragonchain.lib.interfaces.networks.eth.web3.HTTPProvider")
    def test_get_provider_returns_correct_network_dev_eth(self, mock_provider):
        self.client.network = "ETH_ROPSTEN"
        self.client._get_provider()
        mock_provider.assert_called_once_with(eth.Networks.Ropsten.value)

    @patch("dragonchain.lib.interfaces.networks.eth.web3.HTTPProvider")
    def test_get_provider_returns_correct_network_prod_etc(self, mock_provider):
        self.client.network = "ETC_MAINNET"
        self.client._get_provider()
        mock_provider.assert_called_once_with(eth.Networks.Classic.value)

    @patch("dragonchain.lib.interfaces.networks.eth.web3.HTTPProvider")
    def test_get_provider_returns_correct_network_dev_etc(self, mock_provider):
        self.client.network = "ETC_MORDEN"
        self.client._get_provider()
        mock_provider.assert_called_once_with(eth.Networks.Morden.value)

    def test_get_chain_id_returns_correct_network_prod_eth(self):
        response = eth._get_chain_id("ETH_MAINNET")
        self.assertEqual(response, 1)

    def test_get_chain_id_returns_correct_network_dev_eth(self):
        response = eth._get_chain_id("ETH_ROPSTEN")
        self.assertEqual(response, 3)

    def test_get_chain_id_returns_correct_network_prod_etc(self):
        response = eth._get_chain_id("ETC_MAINNET")
        self.assertEqual(response, 61)

    def test_get_chain_id_returns_correct_network_dev_etc(self):
        response = eth._get_chain_id("ETC_MORDEN")
        self.assertEqual(response, 2)

    @patch("dragonchain.lib.interfaces.networks.eth.ETHClient.get_current_block", return_value=1245839)
    def test_is_transaction_confirmed_final(self, mock_get_current_block):
        self.client.w3.eth.getTransaction = MagicMock(return_value={"blockNumber": 1245739})

        response = self.client.is_transaction_confirmed("0xFakeHash")
        self.assertTrue(response)

        self.client.w3.eth.getTransaction.assert_called_once_with("0xFakeHash")
        mock_get_current_block.assert_called_once()

    @patch("dragonchain.lib.interfaces.networks.eth.ETHClient.get_current_block", return_value=1245839)
    def test_is_transaction_confirmed_unconfirmed(self, mock_get_current_block):
        self.client.w3.eth.getTransaction = MagicMock(return_value={"blockNumber": 1245837})

        response = self.client.is_transaction_confirmed("0xFakeHash")
        self.assertFalse(response)

        self.client.w3.eth.getTransaction.assert_called_once_with("0xFakeHash")
        mock_get_current_block.assert_called_once()

    @patch("dragonchain.lib.interfaces.networks.eth.ETHClient.get_current_block", return_value=1245839)
    def test_is_transaction_confirmed_pending(self, mock_get_current_block):
        self.client.w3.eth.getTransaction = MagicMock(return_value={"blockNumber": None})

        response = self.client.is_transaction_confirmed("0xFakeHash")
        self.assertFalse(response)

        self.client.w3.eth.getTransaction.assert_called_once_with("0xFakeHash")
        mock_get_current_block.assert_called_once()

    def test_is_transaction_confirmed_dropped(self):
        self.client.w3.eth.getTransaction = MagicMock(return_value=None)

        response = self.client.is_transaction_confirmed("0xFakeHash")
        self.assertEqual(response, "0xFakeHash")

        self.client.w3.eth.getTransaction.assert_called_once_with("0xFakeHash")

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

import os
import base64
import enum
from typing import Union, Tuple, Dict, Any

import web3
import web3.gas_strategies.time_based
from eth_keys import keys

from dragonchain.lib.interfaces import secrets
from dragonchain import logger

CONFIRMATIONS_CONSIDERED_FINAL = 12
BLOCK_THRESHOLD = (
    30
)  # This is the number of blocks that can pass after posting the transaction before it decides the transaction won't be included in a block and retry

_log = logger.get_logger()


def _get_chain_id(network: str) -> int:
    # This is our network id post ETH/ETC fork
    # Maintain 'eth' and 'etc' values for backwords compatibility
    if network == "ETH_MAINNET":
        return 1
    elif network == "ETH_ROPSTEN":
        return 3
    elif network == "ETC_MAINNET":
        return 61
    elif network == "ETC_MORDEN":
        return 2
    else:
        raise RuntimeError(f"Network {network} is not valid")


def load_address(network: str) -> keys.PrivateKey:
    if network == "ETH_MAINNET":
        private_key = keys.PrivateKey(base64.b64decode(secrets.get_dc_secret("eth-mainnet-private-key")))
    if network == "ETH_ROPSTEN":
        private_key = keys.PrivateKey(base64.b64decode(secrets.get_dc_secret("eth-ropsten-private-key")))
    if network == "ETC_MAINNET":
        private_key = keys.PrivateKey(base64.b64decode(secrets.get_dc_secret("etc-mainnet-private-key")))
    if network == "ETC_MORDEN":
        private_key = keys.PrivateKey(base64.b64decode(secrets.get_dc_secret("etc-morden-private-key")))

    interchain_address = private_key.public_key.to_checksum_address()
    return interchain_address, private_key


class Networks(enum.Enum):
    Mainnet = os.environ.get("ETH_MAINNET_RPC") or "http://internal-Parity-Mainnet-Internal-1844666982.us-west-2.elb.amazonaws.com:8545"
    Classic = os.environ.get("ETC_MAINNET_RPC") or "http://internal-Parity-Classic-Internal-2003699904.us-west-2.elb.amazonaws.com:8545"
    Ropsten = os.environ.get("ETH_ROPSTEN_RPC") or "http://internal-Parity-Ropsten-Internal-1699752391.us-west-2.elb.amazonaws.com:8545"
    Morden = os.environ.get("ETC_MORDEN_RPC") or "http://internal-Parity-Morden-Internal-26081757.us-west-2.elb.amazonaws.com:8545"


class ETHClient(object):
    def __init__(self, network: str):
        self.network = network
        self.provider = self._get_provider()
        self.chain_id = _get_chain_id(self.network)
        self.w3 = web3.Web3(self.provider)
        self.interchain_address, self.private_key = load_address(self.network)
        _log.info(f"[ETHEREUM] Using address: {self.interchain_address}")
        _log.info(f"[ETHEREUM] Using RPC network: {self.provider}")

    def publish_transaction(self, transaction_payload: str) -> Any:
        # Create transaction from transaction_payload
        _log.info(f"[ETHEREUM] this is inside publish_transaction. payload = {transaction_payload}")
        raw_unsigned_transaction = self._create_raw_transaction(transaction_payload)

        # Sign transaction w/ hopper-api
        signed_transaction = self.sign_transaction(raw_unsigned_transaction)

        # Send raw transaction
        transaction = self.w3.eth.sendRawTransaction(signed_transaction)
        return self.w3.toHex(transaction)

    def is_transaction_confirmed(self, transaction_hash: str) -> Union[bool, str]:
        _log.info(f"[ETHEREUM] Getting confirmations for {transaction_hash}")
        transaction = self.w3.eth.getTransaction(transaction_hash)
        if transaction:
            transaction_block_number = transaction["blockNumber"]
            latest_block_number = self.get_current_block()

            _log.info(f"[ETHEREUM] Latest ethereum block number: {latest_block_number}")
            _log.info(f"[ETHEREUM] Block number of transaction: {transaction_block_number}")
            if transaction_block_number and (latest_block_number - transaction_block_number) >= CONFIRMATIONS_CONSIDERED_FINAL:
                return True
        else:
            #  We return the transaction hash if it was dropped from the mempool.
            return transaction_hash

        return False

    def get_current_block(self) -> Any:
        return self.w3.eth.getBlock("latest")["number"]

    def get_retry_threshold(self) -> int:
        return BLOCK_THRESHOLD

    def check_address_balance(self) -> int:
        _log.info(f"[ETHEREUM] Checking balance for {self.interchain_address}")
        return self.w3.eth.getBalance(self.interchain_address)

    def get_transaction_fee_estimate(self) -> int:
        gas_price, gas_limit = self._calculate_transaction_fee()
        return int(gas_price * gas_limit)

    def sign_transaction(self, raw_transaction: Dict[str, Any]) -> str:
        _log.info(f"[ETHEREUM] Signing raw transaction: {raw_transaction}")
        raw_transaction["chainId"] = self.chain_id
        if not raw_transaction.get("nonce"):
            raw_transaction["nonce"] = self.w3.toHex(self.w3.eth.getTransactionCount(self.interchain_address))
        if not raw_transaction.get("gasPrice") or not raw_transaction.get("gas"):
            gas_price, gas_limit = self._calculate_transaction_fee()
            raw_transaction["gasPrice"] = self.w3.toHex(gas_price)
            raw_transaction["gas"] = self.w3.toHex(gas_limit)

        signed = self.w3.eth.account.signTransaction(raw_transaction, self.private_key)
        return signed.rawTransaction.hex()

    def _calculate_transaction_fee(self) -> Tuple[int, int]:
        self.w3.eth.setGasPriceStrategy(web3.gas_strategies.time_based.medium_gas_price_strategy)
        gas_price = 30000000000 if self.network == "etc" else int(self.w3.eth.generateGasPrice())
        _log.info(f"[ETHEREUM] Gas price: {gas_price}")
        gas_limit = 60000
        _log.info(f"[ETHEREUM] Gas limit: {gas_limit}")

        return gas_price, gas_limit

    def _create_raw_transaction(self, payload: str) -> Dict[str, Any]:
        _log.info("[ETHEREUM] Creating raw transaction...")

        raw_txn = {
            "nonce": self.w3.toHex(self.w3.eth.getTransactionCount(self.interchain_address)),
            "to": "0x0000000000000000000000000000000000000000",
            "from": self.interchain_address,
            "value": self.w3.toHex(0),
            "data": self.w3.toHex(payload.encode("utf-8")),
        }

        _log.info(f"[ETHEREUM] Raw transaction: {raw_txn}")

        return raw_txn

    def _get_provider(self) -> web3.HTTPProvider:
        # Maintain 'eth' and 'etc' values for backwords compatibility
        if self.network == "ETH_MAINNET":
            provider = Networks.Mainnet.value
        elif self.network == "ETH_ROPSTEN":
            provider = Networks.Ropsten.value
        elif self.network == "ETC_MAINNET":
            provider = Networks.Classic.value
        elif self.network == "ETC_MORDEN":
            provider = Networks.Morden.value
        else:
            raise RuntimeError("Invalid network specified.")
        return web3.HTTPProvider(provider)

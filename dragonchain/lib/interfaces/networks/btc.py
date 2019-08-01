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
import math
import base64
import enum
from typing import Union, Tuple, Dict, Any

import requests
import bit

from dragonchain.lib.interfaces import secrets
from dragonchain import exceptions
from dragonchain import logger


CONFIRMATIONS_CONSIDERED_FINAL = 6
BLOCK_THRESHOLD = 10  # The number of blocks that can pass by before trying to send another transaction
MINIMUM_SATOSHI_PER_BYTE = 10

_log = logger.get_logger()


def load_address(network: str) -> Tuple[str, bit.wallet.BaseKey]:
    if network == "BTC_MAINNET":
        private_key = bit.Key.from_bytes(base64.b64decode(secrets.get_dc_secret("btc-mainnet-private-key")))
    if network == "BTC_TESTNET3":
        private_key = bit.PrivateKeyTestnet.from_bytes(base64.b64decode(secrets.get_dc_secret("btc-testnet3-private-key")))
    interchain_address = private_key.address
    return interchain_address, private_key


class Networks(enum.Enum):
    Mainnet = os.environ.get("BTC_MAINNET_RPC") or "http://internal-Btc-Mainnet-Internal-297595751.us-west-2.elb.amazonaws.com:8332"
    Testnet = os.environ.get("BTC_TESTNET3_RPC") or "http://internal-Btc-Testnet-Internal-1334656512.us-west-2.elb.amazonaws.com:18332"


class BTCClient(object):
    def __init__(self, network: str):
        self.network = network
        self.endpoint = self._get_network()
        self.auth = base64.b64encode(("bitcoinrpc:dragon").encode("utf-8")).decode("ascii")
        self.interchain_address, self.private_key = load_address(self.network)
        _log.info(f"[BTC] Using address: {self.interchain_address}")
        _log.info(f"[BTC] Using RPC network: {self.endpoint}")

    def publish_transaction(self, transaction_payload: str) -> Any:
        # Create transaction from transaction_payload
        _log.info(f"[BTC] Publishing transaction: payload = {transaction_payload}")
        raw_unsigned_transaction = self._create_raw_transaction(transaction_payload)

        # Sign transaction w/ hopper-api
        signed_transaction = self.sign_transaction(raw_unsigned_transaction)

        # Send raw transaction
        return self.call("sendrawtransaction", signed_transaction)

    def is_transaction_confirmed(self, transaction_hash: str) -> Union[bool, str]:
        _log.info(f"[BTC] Getting confirmations for {transaction_hash}")
        try:
            confirmations = self.call("getrawtransaction", transaction_hash, True).get("confirmations") or 0
        except Exception:
            _log.exception("The transaction may have been dropped.")
            return transaction_hash
        _log.info(f"[BTC] {confirmations} confirmations")
        return confirmations >= CONFIRMATIONS_CONSIDERED_FINAL

    def get_current_block(self) -> Any:
        return self.call("getblockcount")

    def get_retry_threshold(self) -> int:
        return BLOCK_THRESHOLD

    def check_address_balance(self) -> int:
        _log.info(f"[BTC] Checking balance for {self.interchain_address}")
        btc_balance = self.call("getreceivedbyaddress", self.interchain_address, 6)
        return self.btc_to_satoshi(btc_balance)

    def btc_to_satoshi(self, btc: float) -> int:
        return int(btc * 100000000)

    def get_transaction_fee_estimate(self) -> int:
        byte_count = 262
        satoshi_per_byte = self._calculate_transaction_fee()
        return int(byte_count * satoshi_per_byte)

    def sign_transaction(self, raw_transaction: Dict[str, Any]) -> str:
        _log.info(f"[BTC] Signing raw transaction: {raw_transaction}")

        outputs: list = []
        if raw_transaction.get("outputs"):
            outputs = list(map(lambda output: (output["to"], output["value"], "btc"), raw_transaction["outputs"]))

        btc_transaction = self.private_key.create_transaction(
            outputs,
            unspents=self._get_utxos(),
            fee=raw_transaction.get("fee") or self._calculate_transaction_fee(),
            leftover=raw_transaction.get("change") or self.interchain_address,
            message=raw_transaction.get("data"),
        )
        signed_transaction = self.private_key.sign_transaction(btc_transaction)

        return signed_transaction

    def _calculate_transaction_fee(self) -> int:
        resp = self.call("estimatesmartfee", 2)
        satoshi_per_byte = math.ceil(
            self.btc_to_satoshi(resp["feerate"]) / 1024
        )  # feerate is in BTC/kB; divide by 1024 to convert to BTC/byte, then convert to satoshi/byte
        _log.info(f"[BTC] Satoshis/Byte: {satoshi_per_byte}")
        return MINIMUM_SATOSHI_PER_BYTE if satoshi_per_byte < MINIMUM_SATOSHI_PER_BYTE else satoshi_per_byte

    def _create_raw_transaction(self, payload: str) -> Dict[str, str]:
        return {"data": payload.encode("utf-8").hex()}

    def _get_utxos(self) -> list:
        utxos = self.call("listunspent", 1, 9999999, [self.interchain_address])
        if not utxos:
            raise exceptions.NotEnoughCrypto
        utxos = list(
            map(
                lambda utxo: bit.network.meta.Unspent(
                    self.btc_to_satoshi(utxo["amount"]), utxo["confirmations"], utxo["scriptPubKey"], utxo["txid"], utxo["vout"]
                ),
                utxos,
            )
        )
        return utxos

    def _get_network(self) -> str:
        if self.network == "BTC_MAINNET":
            return Networks.Mainnet.value
        elif self.network == "BTC_TESTNET3":
            return Networks.Testnet.value
        else:
            raise RuntimeError(f"Network {self.network} is invalid")

    def register_address(self) -> None:
        registered = self.call("listlabels")
        if self.interchain_address not in registered:
            response = self.call("importaddress", self.interchain_address, self.interchain_address, False)
            if response:
                raise exceptions.AddressRegistrationFailure("Address failed registering")

    def call(self, method: str, *args: Any) -> Any:
        response = requests.post(
            self.endpoint, json={"method": method, "params": list(args), "id": 1}, headers={"Authorization": f"Basic {self.auth}"}, timeout=30
        ).json()
        if response.get("error") or response.get("errors"):
            raise exceptions.RPCError(f"The RPC client got an error response: {response}")
        return response["result"]

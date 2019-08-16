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
from typing import Dict, Any

import web3
import web3.gas_strategies.time_based
import eth_keys

from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib.dto import model

CONFIRMATIONS_CONSIDERED_FINAL = 12
BLOCK_THRESHOLD = 30  # The number of blocks that can pass by before trying to send another transaction
STANDARD_GAS_LIMIT = 60000

_log = logger.get_logger()


def new_from_at_rest(ethereum_network_at_rest: Dict[str, Any]) -> "EthereumNetwork":
    dto_version = ethereum_network_at_rest.get("version")
    if dto_version == "1":
        return EthereumNetwork(
            name=ethereum_network_at_rest["name"],
            network_address=ethereum_network_at_rest["network_address"],
            chain_id=ethereum_network_at_rest["chain_id"],
            b64_private_key=ethereum_network_at_rest["private_key"],
        )
    else:
        raise NotImplementedError(f"DTO version {dto_version} not supported for bitcoin network")


class EthereumNetwork(model.InterchainModel):
    def __init__(self, name: str, network_address: str, chain_id: int, b64_private_key: str):
        self.name = name
        self.network_address = network_address
        self.chain_id = chain_id
        self.priv_key = eth_keys.keys.PrivateKey(base64.b64decode(b64_private_key))
        self.address = self.priv_key.public_key.to_checksum_address()
        self.w3 = web3.Web3(web3.HTTPProvider(self.network_address))
        # Set gas strategy
        self.w3.eth.setGasPriceStrategy(web3.gas_strategies.time_based.medium_gas_price_strategy)

    def sign_transaction(self, raw_transaction: Dict[str, Any]) -> str:
        _log.info(f"[ETHEREUM] Signing raw transaction: {raw_transaction}")
        raw_transaction["chainId"] = self.chain_id
        if not raw_transaction.get("nonce"):
            raw_transaction["nonce"] = self.w3.toHex(self.w3.eth.getTransactionCount(self.address))
        if not raw_transaction.get("gasPrice") or not raw_transaction.get("gas"):
            raw_transaction["gasPrice"] = self.w3.toHex(self._calculate_transaction_fee())
            raw_transaction["gas"] = self.w3.toHex(STANDARD_GAS_LIMIT)
        return self.w3.eth.account.sign_transaction(raw_transaction, self.priv_key).rawTransaction.hex()

    def is_transaction_confirmed(self, transaction_hash: str) -> bool:
        _log.info(f"[ETHEREUM] Getting confirmations for {transaction_hash}")
        try:
            transaction_block_number = self.w3.eth.getTransaction(transaction_hash)["blockNumber"]
        except web3.exceptions.TransactionNotFound:
            raise exceptions.RPCTransactionNotFound(f"Transaction {transaction_hash} not found")
        latest_block_number = self.get_current_block()
        _log.info(f"[ETHEREUM] Latest ethereum block number: {latest_block_number} | Block number of transaction: {transaction_block_number}")
        return transaction_block_number and (latest_block_number - transaction_block_number) >= CONFIRMATIONS_CONSIDERED_FINAL

    def check_balance(self) -> int:
        return self.w3.eth.getBalance(self.address)

    def get_transaction_fee_estimate(self, gas_limit: int = STANDARD_GAS_LIMIT) -> int:
        return int(self._calculate_transaction_fee() * gas_limit)

    def get_current_block(self) -> int:
        return self.w3.eth.getBlock("latest")["number"]

    def should_retry_broadcast(self, last_sent_block: int) -> bool:
        return self.get_current_block() - last_sent_block > BLOCK_THRESHOLD

    def _publish_transaction(self, transaction_payload: str) -> str:
        _log.info(f"[ETHEREUM] Publishing transaction. payload = {transaction_payload}")
        # Sign transaction data
        signed_transaction = self.sign_transaction(
            {
                "nonce": self.w3.toHex(self.w3.eth.getTransactionCount(self.address)),
                "to": "0x0000000000000000000000000000000000000000",
                "from": self.address,
                "value": self.w3.toHex(0),
                "data": self.w3.toHex(transaction_payload.encode("utf-8")),
            }
        )
        # Send signed transaction
        return self.w3.toHex(self.w3.eth.sendRawTransaction(signed_transaction))

    def _calculate_transaction_fee(self) -> int:
        gas_price = int(self.w3.eth.generateGasPrice())
        _log.info(f"[ETHEREUM] Current estimated gas price: {gas_price}")
        return gas_price

    def export_as_at_rest(self) -> Dict[str, Any]:
        return {
            "version": "1",
            "name": self.name,
            "network_address": self.network_address,
            "chain_id": self.chain_id,
            "private_key": base64.b64encode(self.priv_key.to_bytes()).decode("ascii"),
        }

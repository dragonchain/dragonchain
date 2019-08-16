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

import math
import base64
from typing import Optional, Dict, Any

import requests
import bit

from dragonchain.lib.dto import model
from dragonchain import exceptions
from dragonchain import logger


CONFIRMATIONS_CONSIDERED_FINAL = 6
BLOCK_THRESHOLD = 10  # The number of blocks that can pass by before trying to send another transaction
MINIMUM_SATOSHI_PER_BYTE = 10

_log = logger.get_logger()


def new_from_at_rest(bitcoin_network_at_rest: Dict[str, Any]) -> "BitcoinNetwork":
    """Instantiate a new BitcoinNetwork model from storage
    Args:
        bitcoin_network_at_rest: The dto of the at-rest network from storage
    Returns:
        Instantiated BitcoinNetwork client
    Raises:
        NotImplementedError: When the version of the dto passed in is unknown
    """
    dto_version = bitcoin_network_at_rest.get("version")
    if dto_version == "1":
        return BitcoinNetwork(
            name=bitcoin_network_at_rest["name"],
            network_address=bitcoin_network_at_rest["network_address"],
            testnet=bitcoin_network_at_rest["testnet"],
            b64_private_key=bitcoin_network_at_rest["private_key"],
            authorization=bitcoin_network_at_rest["authorization"],
        )
    else:
        raise NotImplementedError(f"DTO version {dto_version} not supported for bitcoin network")


class BitcoinNetwork(model.InterchainModel):
    def __init__(self, name: str, network_address: str, testnet: bool, b64_private_key: str, authorization: Optional[str] = None):
        self.name = name
        self.network_address = network_address
        self.authorization = authorization
        self.testnet = testnet
        if testnet:
            self.priv_key = bit.PrivateKeyTestnet.from_bytes(base64.b64decode(b64_private_key))
        else:
            self.priv_key = bit.Key.from_bytes(base64.b64decode(b64_private_key))

    def sign_transaction(self, raw_transaction: Dict[str, Any]) -> str:
        """Sign a transaction for this network
        Args:
            raw_transaction: The dictionary of the raw transaction containing:
                outputs: Optional list of dictionary of outputs to send btc to various places
                    to: Address to send this bitcoin
                    value: Amount of value to send to this address in btc (int, float, or string)
                fee: Optional integer of satoshis/byte to use for the fee
                change: Optional string of the change address to use (defaults to its own address)
                message: Optional string for arbitrary data to add with this transaction
        Returns:
            Hex string of the signed transaction
        """
        _log.info(f"[BTC] Signing raw transaction: {raw_transaction}")

        outputs: list = []
        if raw_transaction.get("outputs"):
            outputs = [(x["to"], x["value"], "btc") for x in raw_transaction["outputs"]]

        btc_transaction = self.priv_key.create_transaction(
            outputs,
            unspents=self._get_utxos(),
            fee=raw_transaction.get("fee") or self._calculate_transaction_fee(),
            leftover=raw_transaction.get("change") or self.priv_key.address,
            message=raw_transaction.get("data"),
        )
        return self.priv_key.sign_transaction(btc_transaction)

    def is_transaction_confirmed(self, transaction_hash: str) -> bool:
        """Check if a transaction is considered confirmed
        Args:
            transaction_hash: The hash of the transaction to check
        Returns:
            Boolean if the transaction has receieved enough confirmations to be considered confirmed
        Raises:
            exceptions.RPCTransactionNotFound: When the transaction could not be found (may have been dropped)
        """
        _log.info(f"[BTC] Getting confirmations for {transaction_hash}")
        try:
            confirmations = self._call("getrawtransaction", transaction_hash, True).get("confirmations") or 0
        except exceptions.RPCError:
            _log.warning("The transaction may have been dropped.")
            raise exceptions.RPCTransactionNotFound(f"Transaction {transaction_hash} not found")
        _log.info(f"[BTC] {confirmations} confirmations")
        return confirmations >= CONFIRMATIONS_CONSIDERED_FINAL

    def check_balance(self) -> int:
        """Check the balance of the address for this network
        Returns:
            The amount of satoshi in the account
        """
        _log.info(f"[BTC] Checking balance for {self.priv_key.address}")
        btc_balance = self._call("getreceivedbyaddress", self.priv_key.address, CONFIRMATIONS_CONSIDERED_FINAL)
        return btc_to_satoshi(btc_balance)

    def get_transaction_fee_estimate(self, byte_count: int = 262) -> int:
        """Calculate the transaction fee estimate for a transaction given current fee rates
        Args:
            byte_count: The number of bytes for the transaction to use for this calculation. Defaults to 262
        Returns:
            The amount of estimated transaction fee cost in satoshis
        """
        satoshi_per_byte = self._calculate_transaction_fee()
        return int(byte_count * satoshi_per_byte)

    def get_current_block(self) -> int:
        """Get the current latest block number of the network
        Returns:
            The latest known mined block number on the network
        """
        return self._call("getblockcount")

    def should_retry_broadcast(self, last_sent_block: int) -> bool:
        """Check whether a new broadcast should be attempted, given a number of blocks past (for L5)
        Args:
            last_sent_block: The block when the transaction was last attempted to be sent
        Returns:
            Boolean whether a broadcast should be re-attempted
        """
        return self.get_current_block() - last_sent_block > BLOCK_THRESHOLD

    def register_address(self, scan: bool = False) -> None:
        """Register this network's address with it's bitcoin node to watch for UTXOs
        Args:
            scan: Boolean whether or not to scan the blockchain for existing UTXOs
                This is necessary if the address that's being imported already has funds. This can take a long time (10+ minutes)
        Raises:
            exceptions.AddressRegistrationFailure: When the bitcoin node failed to register the address
        """
        registered = self._call("listlabels")
        if self.priv_key.address not in registered:
            response = self._call("importaddress", self.priv_key.address, self.priv_key.address, scan)
            # Note: False on import address prevents scanning for existing utxos. If the wallet already exists with funds,
            # this needs to be True instead of False, which can take a long time (10+ minutes) to run
            if response:  # Returns null on success
                raise exceptions.AddressRegistrationFailure("Address failed registering")

    def _publish_transaction(self, transaction_payload: str) -> str:
        """Publish a transaction to this network with a certain data payload
        Args:
            transaction_payload: The arbitrary data to send with this transaction
        Returns:
            The string of the published transaction hash
        """
        _log.info(f"[BTC] Publishing transaction: payload = {transaction_payload}")
        # Sign transaction data
        signed_transaction = self.sign_transaction({"data": transaction_payload})
        # Send signed transaction
        return self._call("sendrawtransaction", signed_transaction)

    def _calculate_transaction_fee(self) -> int:
        """Get the current satoshi/byte fee estimate
        Returns:
            satoshi/byte fee estimate
        """
        resp = self._call("estimatesmartfee", 2)
        satoshi_per_byte = math.ceil(
            btc_to_satoshi(resp["feerate"]) / 1024
        )  # feerate is in BTC/kB; divide by 1024 to convert to BTC/byte, then convert to satoshi/byte
        _log.info(f"[BTC] Satoshis/Byte: {satoshi_per_byte}")
        return MINIMUM_SATOSHI_PER_BYTE if satoshi_per_byte < MINIMUM_SATOSHI_PER_BYTE else satoshi_per_byte

    def _get_utxos(self) -> list:
        """Get the utxos for this address
           Note: This address must have been registered with the node (with register_address) for this to work
        Returns:
            List of bit UTXO objects
        """
        utxos = self._call("listunspent", 1, 9999999, [self.priv_key.address])
        if not utxos:
            raise exceptions.NotEnoughCrypto
        return [
            bit.network.meta.Unspent(btc_to_satoshi(utxo["amount"]), utxo["confirmations"], utxo["scriptPubKey"], utxo["txid"], utxo["vout"])
            for utxo in utxos
        ]

    def _call(self, method: str, *args: Any) -> Any:
        """Call the remote bitcoin node RPC with a method and parameters
        Args:
            method: The bitcoin json rpc method to call
            args: The arbitrary arguments for the method (in order)
        Returns:
            The result from the rpc call
        Raises:
            exceptions.RPCError: If the remote call returned an error
        """
        response = requests.post(
            self.network_address,
            json={"method": method, "params": list(args), "id": "1", "jsonrpc": "1.0"},
            headers={"Authorization": f"Basic {self.authorization}"},
            timeout=30,
        ).json()
        if response.get("error") or response.get("errors"):
            raise exceptions.RPCError(f"The RPC client got an error response: {response}")
        return response["result"]

    def export_as_at_rest(self) -> Dict[str, Any]:
        """Export this network to be saved in storage
        Returns:
            DTO as a dictionary to be saved
        """
        return {
            "version": "1",
            "name": self.name,
            "network_address": self.network_address,
            "authorization": self.authorization,
            "testnet": self.testnet,
            "private_key": base64.b64encode(self.priv_key.to_bytes()).decode("ascii"),
        }


def btc_to_satoshi(btc: float) -> int:
    """Convert a btc value to satoshis
    Args:
        btc: The amount of btc to convert
    Returns:
        The integer of satoshis for this conversion
    """
    return int(btc * 100000000)

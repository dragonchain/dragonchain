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

import secp256k1
import requests
import bit

from dragonchain.lib.dto import model
from dragonchain import exceptions
from dragonchain import logger


DRAGONCHAIN_MAINNET_NODE = "http://internal-Btc-Mainnet-Internal-297595751.us-west-2.elb.amazonaws.com:8332"
DRAGONCHAIN_TESTNET_NODE = "http://internal-Btc-Testnet-Internal-1334656512.us-west-2.elb.amazonaws.com:18332"
DRAGONCHAIN_NODE_AUTHORIZATION = "Yml0Y29pbnJwYzpkcmFnb24="  # Username: bitcoinrpc | Password: dragon

CONFIRMATIONS_CONSIDERED_FINAL = 6
BLOCK_THRESHOLD = 10  # The number of blocks that can pass by before trying to send another transaction
MINIMUM_SATOSHI_PER_BYTE = 10

_log = logger.get_logger()


def new_from_user_input(user_input: Dict[str, Any]) -> "BitcoinNetwork":
    """Create a new BitcoinNetwork model from user input
    Args:
        user_input: User dictionary input (assumed already passing create_bitcoin_interchain_schema)
    Returns:
        Instantiated BitcoinNetwork client
    Raises:
        exceptions.BadRequest: With bad input
    """
    dto_version = user_input.get("version")
    if dto_version == "1":
        if not user_input.get("private_key"):
            # We need to create a private key if not provided
            user_input["private_key"] = base64.b64encode(secp256k1.PrivateKey().private_key).decode("ascii")
            user_input["utxo_scan"] = False
        try:
            # Check if the provided private key is in WIF format
            key = bit.wif_to_key(user_input["private_key"])
            testnet = key.version == "test"
            if isinstance(user_input.get("testnet"), bool) and testnet != user_input["testnet"]:
                raise exceptions.BadRequest(f"WIF key was {'testnet' if testnet else 'mainnet'} which doesn't match provided testnet bool")
            # Extract values from WIF
            user_input["testnet"] = testnet
            user_input["private_key"] = base64.b64encode(key.to_bytes()).decode("ascii")
        except Exception as e:
            if isinstance(e, exceptions.BadRequest):
                raise
            # Provided key is not WIF
            if not isinstance(user_input.get("testnet"), bool):
                raise exceptions.BadRequest("Parameter boolean 'testnet' must be provided if key is not WIF")

        # Check for bitcoin node address
        if not user_input.get("rpc_address"):
            # Default to Dragonchain managed nodes if not provided
            user_input["rpc_address"] = DRAGONCHAIN_TESTNET_NODE if user_input["testnet"] else DRAGONCHAIN_MAINNET_NODE
            user_input["rpc_authorization"] = DRAGONCHAIN_NODE_AUTHORIZATION

        # Create the actual client and check that the given node is reachable
        try:
            client = BitcoinNetwork(
                name=user_input["name"],
                testnet=user_input["testnet"],
                b64_private_key=user_input["private_key"],
                rpc_address=user_input["rpc_address"],
                authorization=user_input.get("rpc_authorization"),  # Can be none
            )
        except Exception:
            raise exceptions.BadRequest("Provided private key did not successfully decode into a valid key")
        # First check that the bitcoin node is reachable
        try:
            client.ping()
        except Exception as e:
            raise exceptions.BadRequest(f"Provided bitcoin node doesn't seem reachable. Error: {e}")
        # Now finally register the given address
        try:
            client.register_address(user_input.get("utxo_scan") or False)
        except exceptions.RPCError as e:
            raise exceptions.BadRequest(f"Error registering address with bitcoin node. Error: {e}")

        return client
    else:
        raise exceptions.BadRequest(f"User input version {dto_version} not supported")


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
            rpc_address=bitcoin_network_at_rest["rpc_address"],
            testnet=bitcoin_network_at_rest["testnet"],
            b64_private_key=bitcoin_network_at_rest["private_key"],
            authorization=bitcoin_network_at_rest["authorization"],
        )
    else:
        raise NotImplementedError(f"DTO version {dto_version} not supported for bitcoin network")


class BitcoinNetwork(model.InterchainModel):
    def __init__(self, name: str, rpc_address: str, testnet: bool, b64_private_key: str, authorization: Optional[str] = None):
        self.blockchain = "bitcoin"
        self.name = name
        self.rpc_address = rpc_address
        self.authorization = authorization
        self.testnet = testnet
        if testnet:
            self.priv_key = bit.PrivateKeyTestnet.from_bytes(base64.b64decode(b64_private_key))
        else:
            self.priv_key = bit.Key.from_bytes(base64.b64decode(b64_private_key))
        self.address = self.priv_key.address

    def ping(self) -> None:
        """Ping this network to check if the given node is reachable and authorization is correct (raises exception if not)"""
        self._call("ping")

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
            leftover=raw_transaction.get("change") or self.address,
            message=raw_transaction.get("data"),
        )
        return self.priv_key.sign_transaction(btc_transaction)

    def is_transaction_confirmed(self, transaction_hash: str) -> bool:
        """Check if a transaction is considered confirmed
        Args:
            transaction_hash: The hash of the transaction to check
        Returns:
            Boolean if the transaction has received enough confirmations to be considered confirmed
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
        _log.info(f"[BTC] Checking balance for {self.address}")
        btc_balance = self._call("getreceivedbyaddress", self.address, CONFIRMATIONS_CONSIDERED_FINAL)
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
        if self.address not in registered:
            response = self._call("importaddress", self.address, self.address, scan)
            # Note: False on import address prevents scanning for existing utxos. If the wallet already exists with funds,
            # this needs to be True instead of False, which can take a long time (10+ minutes) to run
            if response:  # Returns null on success
                raise exceptions.AddressRegistrationFailure("Address failed registering")

    def get_network_string(self) -> str:
        """Get the network string for this blockchain. This is what's included in l5 blocks or sent to matchmaking
        Returns:
            Network string
        """
        return f"bitcoin {'testnet3' if self.testnet else 'mainnet'}"

    def get_private_key(self) -> str:
        """Get the base64 encoded private key for this network
        Returns:
            Base64 encoded string of the private key
        """
        return base64.b64encode(self.priv_key.to_bytes()).decode("ascii")

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
        utxos = self._call("listunspent", 1, 9999999, [self.address])
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
        # Note: Even though sending json, documentation still says to use text/plain content type header
        # https://bitcoin.org/en/developer-reference#remote-procedure-calls-rpcs
        r = requests.post(
            self.rpc_address,
            json={"method": method, "params": list(args), "id": "1", "jsonrpc": "1.0"},
            headers={"Authorization": f"Basic {self.authorization}", "Content-Type": "text/plain"},
            timeout=30,
        )
        if r.status_code != 200:
            raise exceptions.RPCError(f"Error from bitcoin node with http status code {r.status_code} | {r.text}")
        response = r.json()
        if response.get("error") or response.get("errors"):
            raise exceptions.RPCError(f"The RPC call got an error response: {response}")
        return response["result"]

    def export_as_at_rest(self) -> Dict[str, Any]:
        """Export this network to be saved in storage
        Returns:
            DTO as a dictionary to be saved
        """
        return {
            "version": "1",
            "blockchain": self.blockchain,
            "name": self.name,
            "rpc_address": self.rpc_address,
            "authorization": self.authorization,
            "testnet": self.testnet,
            "private_key": self.get_private_key(),
        }


def btc_to_satoshi(btc: float) -> int:
    """Convert a btc value to satoshis
    Args:
        btc: The amount of btc to convert
    Returns:
        The integer of satoshis for this conversion
    """
    return int(btc * 100000000)

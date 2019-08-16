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

import secp256k1
import web3
import web3.gas_strategies.time_based
import eth_keys

from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib.dto import model

# Mainnet ETH
DRAGONCHAIN_MAINNET_NODE = "http://internal-Parity-Mainnet-Internal-1844666982.us-west-2.elb.amazonaws.com:8545"
# Testnet ETH
DRAGONCHAIN_ROPSTEN_NODE = "http://internal-Parity-Ropsten-Internal-1699752391.us-west-2.elb.amazonaws.com:8545"
# Mainnet ETC
DRAGONCHAIN_CLASSIC_NODE = "http://internal-Parity-Classic-Internal-2003699904.us-west-2.elb.amazonaws.com:8545"
# Testnet ETC
DRAGONCHAIN_MORDEN_NODE = "http://internal-Parity-Morden-Internal-26081757.us-west-2.elb.amazonaws.com:8545"


CONFIRMATIONS_CONSIDERED_FINAL = 12
BLOCK_THRESHOLD = 30  # The number of blocks that can pass by before trying to send another transaction
STANDARD_GAS_LIMIT = 60000

_log = logger.get_logger()


def new_from_user_input(user_input: Dict[str, Any]) -> "EthereumNetwork":
    """Create a new EthereumNetwork model from user input
    Args:
        user_input: User dictionary input (assumed already passing create_ethereum_interchain_schema)
    Returns:
        Instantiated EthereumNetwork client
    Raises:
        exceptions.BadRequest: With bad input
    """
    dto_version = user_input.get("version")
    if dto_version == "1":
        if not user_input.get("private_key"):
            # We need to create a private key if not provided
            user_input["private_key"] = base64.b64encode(secp256k1.PrivateKey().private_key).decode("ascii")
        else:
            try:
                # Check if user provided key is hex and convert if necessary
                if len(user_input["private_key"]) == 66:  # Ethereum private keys in hex are 66 chars with leading 0x
                    user_input["private_key"] = user_input["private_key"][2:]  # Trim the 0x
                if len(user_input["private_key"]) == 64:  # Ethereum private keys in hex are 64 chars
                    user_input["private_key"] = base64.b64encode(bytes.fromhex(user_input["private_key"])).decode("ascii")
            except Exception:
                # If there's an error here, it's a bad key. Just set it to something bad as bad keys are caught later when making the client
                user_input["private_key"] = "a"
        # Use preset rpc addresses if user didn't provide one
        if not user_input.get("rpc_address"):
            if user_input.get("chain_id") == 1:
                user_input["rpc_address"] = DRAGONCHAIN_MAINNET_NODE
            elif user_input.get("chain_id") == 3:
                user_input["rpc_address"] = DRAGONCHAIN_ROPSTEN_NODE
            elif user_input.get("chain_id") == 61:
                user_input["rpc_address"] = DRAGONCHAIN_CLASSIC_NODE
                user_input["chain_id"] = 1  # Our parity ETC mainnet node reports chain id 1
            elif user_input.get("chain_id") == 2:
                user_input["rpc_address"] = DRAGONCHAIN_MORDEN_NODE
            else:
                raise exceptions.BadRequest(
                    "If an rpc address is not provided, a valid chain id must be provided. ETH_MAIN = 1, ETH_ROPSTEN = 3, ETC_MAIN = 61, ETC_MORDEN = 2"
                )
        # Create our client with a still undetermined chain id
        try:
            client = EthereumNetwork(
                name=user_input["name"], rpc_address=user_input["rpc_address"], b64_private_key=user_input["private_key"], chain_id=0
            )
        except Exception:
            raise exceptions.BadRequest("Provided private key did not successfully decode into a valid key")
        # Check that we can connect and get the rpc's reported chain id
        try:
            reported_chain_id = client.check_rpc_chain_id()
        except Exception as e:
            raise exceptions.BadRequest(f"Error trying to contact ethereum rpc node. Error: {e}")
        # Sanity check if user provided chain id that it matches the what the RPC node reports
        if user_input.get("chain_id") and user_input["chain_id"] != reported_chain_id:
            raise exceptions.BadRequest(f"User provided chain id {user_input['chain_id']}, but RPC reported chain id {reported_chain_id}")
        # Now set the chain id after it's been checked
        client.chain_id = reported_chain_id
        return client
    else:
        raise exceptions.BadRequest(f"User input version {dto_version} not supported")


def new_from_at_rest(ethereum_network_at_rest: Dict[str, Any]) -> "EthereumNetwork":
    """Instantiate a new EthereumNetwork model from storage
    Args:
        ethereum_network_at_rest: The dto of the at-rest network from storage
    Returns:
        Instantiated EthereumNetwork client
    Raises:
        NotImplementedError: When the version of the dto passed in is unknown
    """
    dto_version = ethereum_network_at_rest.get("version")
    if dto_version == "1":
        return EthereumNetwork(
            name=ethereum_network_at_rest["name"],
            rpc_address=ethereum_network_at_rest["rpc_address"],
            chain_id=ethereum_network_at_rest["chain_id"],
            b64_private_key=ethereum_network_at_rest["private_key"],
        )
    else:
        raise NotImplementedError(f"DTO version {dto_version} not supported for bitcoin network")


class EthereumNetwork(model.InterchainModel):
    def __init__(self, name: str, rpc_address: str, chain_id: int, b64_private_key: str):
        self.name = name
        self.rpc_address = rpc_address
        self.chain_id = chain_id
        self.priv_key = eth_keys.keys.PrivateKey(base64.b64decode(b64_private_key))
        self.address = self.priv_key.public_key.to_checksum_address()
        self.w3 = web3.Web3(web3.HTTPProvider(self.rpc_address))
        # Set gas strategy
        self.w3.eth.setGasPriceStrategy(web3.gas_strategies.time_based.medium_gas_price_strategy)

    def check_rpc_chain_id(self) -> int:
        """Get the network ID that the RPC node returns. This can also act as a ping for the RPC"""
        return int(self.w3.net.version)

    def sign_transaction(self, raw_transaction: Dict[str, Any]) -> str:
        """Sign a transaction for this network
        Args:
            raw_transaction: The dictionary of the raw transaction containing:
                to: hex string of the to address
                value: The amount of eth (in wei) to send (in hex string)
                data: Optional hex string for arbitrary data
                nonce: Optional field for nonce (will automatically determine if not provided)
                gasPrice: Optional field to set gasPrice of the transaction (as a hex string in wei)
                gas: Optional gas limit for this transaction (as a hex string). Defaults to 60000
        Returns:
            String of the signed transaction as hex
        """
        _log.info(f"[ETHEREUM] Signing raw transaction: {raw_transaction}")
        raw_transaction["from"] = self.address
        raw_transaction["chainId"] = self.chain_id
        if not raw_transaction.get("nonce"):
            raw_transaction["nonce"] = self.w3.toHex(self.w3.eth.getTransactionCount(self.address))
        if not raw_transaction.get("gasPrice"):
            raw_transaction["gasPrice"] = self.w3.toHex(self._calculate_transaction_fee())
        if not raw_transaction.get("gas"):
            raw_transaction["gas"] = self.w3.toHex(STANDARD_GAS_LIMIT)
        return self.w3.eth.account.sign_transaction(raw_transaction, self.priv_key).rawTransaction.hex()

    def is_transaction_confirmed(self, transaction_hash: str) -> bool:
        """Check if a transaction is considered confirmed
        Args:
            transaction_hash: The hash of the transaction to check
        Returns:
            Boolean if the transaction has receieved enough confirmations to be considered confirmed
        Raises:
            exceptions.RPCTransactionNotFound: When the transaction could not be found (may have been dropped)
        """
        _log.info(f"[ETHEREUM] Getting confirmations for {transaction_hash}")
        try:
            transaction_block_number = self.w3.eth.getTransaction(transaction_hash)["blockNumber"]
        except web3.exceptions.TransactionNotFound:
            raise exceptions.RPCTransactionNotFound(f"Transaction {transaction_hash} not found")
        latest_block_number = self.get_current_block()
        _log.info(f"[ETHEREUM] Latest ethereum block number: {latest_block_number} | Block number of transaction: {transaction_block_number}")
        return transaction_block_number and (latest_block_number - transaction_block_number) >= CONFIRMATIONS_CONSIDERED_FINAL

    def check_balance(self) -> int:
        """Check the balance of the address for this network
        Returns:
            The amount of wei in the account
        """
        return self.w3.eth.getBalance(self.address)

    def get_transaction_fee_estimate(self, gas_limit: int = STANDARD_GAS_LIMIT) -> int:
        """Calculate the transaction fee estimate for a transaction given current fee rates
        Args:
            gas_limit: The gas limit to use for this calculation. Defaults to 60000
        Returns:
            The amount of estimated transaction fee cost in wei
        """
        return int(self._calculate_transaction_fee() * gas_limit)

    def get_current_block(self) -> int:
        """Get the current latest block number of the network
        Returns:
            The latest known mined block number on the network
        """
        return self.w3.eth.getBlock("latest")["number"]

    def should_retry_broadcast(self, last_sent_block: int) -> bool:
        """Check whether a new broadcast should be attempted, given a number of blocks past (for L5)
        Args:
            last_sent_block: The block when the transaction was last attempted to be sent
        Returns:
            Boolean whether a broadcast should be re-attempted
        """
        return self.get_current_block() - last_sent_block > BLOCK_THRESHOLD

    def _publish_transaction(self, transaction_payload: str) -> str:
        """Publish a transaction to this network with a certain data payload
        Args:
            transaction_payload: The arbitrary data to send with this transaction
        Returns:
            The hex string of the published transaction hash
        """
        _log.info(f"[ETHEREUM] Publishing transaction. payload = {transaction_payload}")
        # Sign transaction data
        signed_transaction = self.sign_transaction(
            {
                "to": "0x0000000000000000000000000000000000000000",
                "value": self.w3.toHex(0),
                "data": self.w3.toHex(transaction_payload.encode("utf-8")),
            }
        )
        # Send signed transaction
        return self.w3.toHex(self.w3.eth.sendRawTransaction(signed_transaction))

    def _calculate_transaction_fee(self) -> int:
        """Get the current gas price estimate
        Returns:
            Gas price estimate in wei
        """
        gas_price = int(self.w3.eth.generateGasPrice())
        _log.info(f"[ETHEREUM] Current estimated gas price: {gas_price}")
        return gas_price

    def export_as_at_rest(self) -> Dict[str, Any]:
        """Export this network to be saved in storage
        Returns:
            DTO as a dictionary to be saved
        """
        return {
            "version": "1",
            "blockchain": "ethereum",
            "name": self.name,
            "rpc_address": self.rpc_address,
            "chain_id": self.chain_id,
            "private_key": base64.b64encode(self.priv_key.to_bytes()).decode("ascii"),
        }

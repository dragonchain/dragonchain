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

from typing import Dict, Any
import base64
import binascii

from binance_chain.messages import TransferMsg, Signature
from binance_chain.wallet import Wallet
from binance_chain.environment import BinanceEnvironment
import requests

from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib.dto import model


DC_MAINNET_NODE = "http://10.2.1.53"  # Mainnet BNB
DC_TESTNET_NODE = "https://data-seed-pre-0-s3.binance.org"  # Testnet BNB
# we currently don't have a private testnet node set up...

MAINNET_RPC_PORT = "27147"
MAINNET_API_PORT = "1169"
TESTNET_RPC_PORT = "443"  # FIXME:  add in to user setup / testnet boolean conditional
TESTNET_API_PORT = ""  # FIXME: unfortunately I don't think there are public testnet API-server endpoints...

CONFIRMATIONS_CONSIDERED_FINAL = 1  # https://docs.binance.org/faq.html#what-is-the-design-principle-of-binance-chain
BLOCK_THRESHOLD = 3  # The number of blocks that can pass by before trying to send another transaction
SEND_FEE = 37500  # transfer fee fixed at 0.000375 BNB : https://docs.binance.org/trading-spec.html#current-fees-table-on-mainnet

_log = logger.get_logger()


def new_from_user_input(user_input: Dict[str, Any]) -> "BinanceNetwork":
    """Create a new BinanceNetwork model from user input
    Args:
        user_input: User dictionary input (assumed already passing create_binance_interchain_schema)
    Returns:
        Instantiated BinanceNetwork client
    Raises:
        exceptions.BadRequest: With bad input
    """
    dto_version = user_input.get("version")
    if dto_version == "1":
        if not user_input.get("private_key"):
            # We need to create a private key if not provided
            wallet = Wallet.create_random_wallet()
            user_input["private_key"] = base64.b64encode(binascii.unhexlify(wallet.private_key)).decode("ascii")
        else:
            try:
                # Check if user provided key is hex and convert if necessary
                if len(user_input["private_key"]) == 66:  # private keys in hex are 66 chars with leading 0x
                    user_input["private_key"] = user_input["private_key"][2:]  # Trim the 0x
                if len(user_input["private_key"]) == 64:  # private keys in hex are 64 chars
                    user_input["private_key"] = base64.b64encode(binascii.unhexlify(user_input["private_key"])).decode("ascii")
                else:  # assume key is a mnemonic string
                    wallet = Wallet.create_wallet_from_mnemonic(user_input.get("private_key"))
                    user_input["private_key"] = base64.b64encode(binascii.unhexlify(wallet.private_key)).decode("ascii")
            except Exception:
                # If there's an error here, it's a bad key. Sets it to a bad key, will be caught later when making the client
                user_input["private_key"] = "BAD_KEY_WAS_FOUND"

        # check for user-provided node address
        if not user_input.get("node_ip"):
            # default to Dragonchain managed Binance node if not provided
            user_input["node_ip"] = DC_TESTNET_NODE if user_input.get("testnet") else DC_MAINNET_NODE
            user_input["rpc_port"] = TESTNET_RPC_PORT if user_input.get("testnet") else MAINNET_RPC_PORT
            user_input["api_port"] = TESTNET_API_PORT if user_input.get("testnet") else MAINNET_API_PORT
        else:
            # accept port #s from user, then fix formatting behind the scenes for them to work
            user_input["rpc_port"] = user_input["rpc_port"]
            user_input["api_port"] = user_input["api_port"]
        # check if user specified that node is a testnet
        if user_input.get("testnet") is None:
            user_input["testnet"] = True  # default to testnet
        # Create the actual client and check that the given node is reachable
        try:
            client = BinanceNetwork(
                name=user_input["name"],
                testnet=user_input["testnet"],
                node_ip=user_input["node_ip"],
                rpc_port=user_input["rpc_port"],
                api_port=user_input["api_port"],
                b64_private_key=user_input["private_key"],
            )
        except Exception:
            _log.exception(f"[BINANCE] Exception thrown during key handling.  Bad key: {user_input['private_key']}")
            raise exceptions.BadRequest("Provided private key did not successfully decode into a valid key")
        # check that the binance node is reachable (this checks both RPC and API endpoints)
        try:
            client.ping()
        except Exception as e:
            raise exceptions.BadRequest(f"Provided binance node doesn't seem reachable. Error: {e}")
        return client
    else:
        raise exceptions.BadRequest(f"User input version {dto_version} not supported")


def new_from_at_rest(binance_network_at_rest: Dict[str, Any]) -> "BinanceNetwork":
    """Instantiate a new BinanceNetwork model from storage
    Args:
        binance_network_at_rest: The dto of the at-rest network from storage
    Returns:
        Instantiated BinanceNetwork client
    Raises:
        NotImplementedError: When the version of the dto passed in is unknown
    """
    dto_version = binance_network_at_rest.get("version")
    if dto_version == "1":
        return BinanceNetwork(
            name=binance_network_at_rest["name"],
            testnet=binance_network_at_rest["testnet"],
            node_ip=binance_network_at_rest["node_ip"],
            rpc_port=binance_network_at_rest["rpc_port"],
            api_port=binance_network_at_rest["api_port"],
            b64_private_key=binance_network_at_rest["private_key"],
        )
    else:
        raise NotImplementedError(f"DTO version {dto_version} not supported for binance network")


class BinanceNetwork(model.InterchainModel):
    def __init__(self, name: str, testnet: bool, node_ip: str, rpc_port: str, api_port: str, b64_private_key: str):
        self.blockchain = "binance"
        self.name = name
        self.testnet = testnet
        self.node_ip = node_ip
        self.rpc_port = rpc_port
        self.api_port = api_port

        if testnet:
            testnet_env = BinanceEnvironment(api_url=api_port, hrp="tbnb")
            self.wallet = Wallet(binascii.hexlify(base64.b64decode(b64_private_key)).decode("ascii"), env=testnet_env)
        else:
            prod_env = BinanceEnvironment(api_url=api_port, hrp="bnb")
            self.wallet = Wallet(binascii.hexlify(base64.b64decode(b64_private_key)).decode("ascii"), env=prod_env)

        self.address = self.wallet.address

    def ping(self) -> None:
        """Ping this network to check if the given node is reachable and authorization is correct (raises exception if not)"""
        self._call_node_rpc("status", {})
        self._call_node_api("tokens/BNB")

    # https://docs.binance.org/api-reference/node-rpc.html#6114-query-tx
    def is_transaction_confirmed(self, transaction_hash: str) -> bool:
        """Check if a transaction is considered confirmed
        Args:
            transaction_hash: The hash (or equivalent, i.e. id) of the transaction to check
        Returns:
            Boolean if the transaction has received enough confirmations to be considered confirmed
        Raises:
            exceptions.TransactionNotFound: When the transaction could not be found (may have been dropped)
        """
        _log.info(f"[BINANCE] Getting confirmations for {transaction_hash}")
        # TODO: will this function be called with a txn hash that has this prepended already?   do I need a conditional check?
        # transaction_hash = f"0x{transaction_hash}"  # GET call needs this in front of the hash
        try:
            response = self._call_node_rpc("tx", {"hash": transaction_hash, "prove": "true"})
            transaction_block_number = response["result"]["height"]
        except exceptions.InterchainConnectionError:
            raise exceptions.TransactionNotFound(f"Transaction {transaction_hash} not found")
        latest_block_number = self.get_current_block()
        _log.info(f"[BINANCE] Latest block number: {latest_block_number} | Block number of transaction: {transaction_block_number}")
        return transaction_block_number and (latest_block_number - transaction_block_number) >= CONFIRMATIONS_CONSIDERED_FINAL

    # https://docs.binance.org/api-reference/api-server.html#apiv1balanceaddresssymbol
    def check_balance(self, symbol: str = "BNB") -> int:
        """Check the balance of the address for this network
        Args:
            symbol: stock ticker symbol for token you're trying to check the balance of
        Returns:
            The amount of funds of that token in the wallet
        """
        _log.info(f"[BNB] Checking {symbol} balance for {self.address}")
        path = f"balances/{self.address}/{symbol}"  # params not handled in typical way
        response = self._call_node_api(path)
        bnb_balance = response["balance"]["free"]
        return bnb_balance

    # https://docs.binance.org/api-reference/api-server.html#apiv1fees
    def get_transaction_fee(self) -> int:
        """Calculate the transaction fee estimate for a transaction given current fee rates
        Returns:
            The amount of estimated transaction fee cost for the network
        """
        _log.info("Double checking the send fee...")
        response = self._call_node_api("fees")
        for fee_block in response:
            if "fixed_fee_params" in fee_block:
                if fee_block["fixed_fee_params"]["msg_type"] == "send":
                    return fee_block["fixed_fee_params"]["fee"]  # fixed fee: 37500 (0.000375 BNB)
        _log.info("Double-check failed; resorting to saved fee value.")
        return SEND_FEE  # SET GLOBALLY

    # https://docs.binance.org/api-reference/node-rpc.html#6110-query-block
    def get_current_block(self) -> int:
        """Get the current latest block number of the network
        Returns:
            The latest known block number on the network
        """
        # if no "height" parameter is provided, latest block is fetched
        response = self._call_node_rpc("block", {})
        current_block = response["result"]["block"]["header"]["height"]
        # current_block = json_data.result.block.header.height
        return current_block

    def should_retry_broadcast(self, last_sent_block: int) -> bool:
        """Check whether a new broadcast should be attempted, given a number of blocks past (for L5)
        Args:
            last_sent_block: The block when the transaction was last attempted to be sent
        Returns:
            Boolean whether a broadcast should be re-attempted
        """
        return self.get_current_block() - last_sent_block > BLOCK_THRESHOLD

    def get_network_string(self) -> str:
        """Get the network string for this blockchain. This is what's included in l5 blocks or sent to matchmaking
        Returns:
            Network string
        """
        return f"binance {'testnet' if self.testnet else 'mainnet'}"

    def get_private_key(self) -> str:
        """Get the private key for this network
        Returns:
            string of the private key
        """
        return base64.b64encode(binascii.unhexlify(self.wallet.private_key)).decode("ascii")

    def sign_transaction(self, raw_transaction: Dict[str, Any]) -> str:
        """Sign a transaction for this network
        Args:
            raw_transaction: The dictionary of the raw transaction containing:
                to: hex string of the to address
                symbol: the exchange symbol for the token (NOT defaulted to BNB)
                amount:  amount of token in transaction
                to_address:  address sending tokens to
                memo: Optional string of arbitrary data

                value: The amount of eth (in wei) to send (in hex string)
        Returns:
            String of the signed transaction as hex
        """
        transfer_msg = TransferMsg(
            wallet=self.wallet,
            symbol=raw_transaction["symbol"],
            amount=raw_transaction["amount"],
            to_address=raw_transaction["to_address"],
            memo=raw_transaction.get("memo"),  # optional, don't error if it's missing
        )
        try:
            _log.info(f"[BINANCE] Signing raw transaction: {transfer_msg}")
            return Signature(transfer_msg).sign()  # signed transaction
        except Exception as e:
            raise exceptions.BadRequest(f"Error signing transaction: {e}")

    def _publish_transaction(self, transaction_payload: str) -> str:
        """Publish a transaction to this network with a certain data payload
        Args:
            transaction_payload: The arbitrary data to send with this transaction
        Returns:
            The string of the published transaction hash
        """
        _log.info(f"[BINANCE] Publishing transaction. payload = {transaction_payload}")

        # Sign transaction data
        dummy = "0x0000000000000000000000000000000000000000"
        transfer_msg = TransferMsg(wallet=self.wallet, symbol="BNB", amount=0, to_address=dummy, memo=transaction_payload)

        # Send signed transaction
        response = self._call_node_rpc("broadcast_tx_commit", {"tx": transfer_msg})
        return response["result"]["hash"]  # transaction hash

    # endpoints currently hit are:
    #     "status" (ping check)
    #     "tx" (block number check)
    #     "block" (latest block check)
    #     "broadcast_tx_commit" (submit txn)
    def _call_node_rpc(self, method: str, params: Dict[str, Any]) -> Any:
        full_address = f"{self.node_ip}:{self.rpc_port}/"
        body = {"method": method, "jsonrpc": "2.0", "params": params, "id": "dontcare"}
        r = requests.post(full_address, json=body, timeout=30)
        response = self._get_response(r)
        return response

    # endpoints currently hit are:
    #     "tokens" (ping check)
    #     "fees" (fee check)
    #     "balances" (tokens in address check)
    def _call_node_api(self, path: str) -> Any:
        full_address = f"{self.node_ip}:{self.api_port}/api/v1/{path}"
        r = requests.get(full_address, timeout=30)
        response = self._get_response(r)
        return response

    def _get_response(self, r: requests.Response) -> Any:
        error_status = f"Error from binance node with http status code {r.status_code} | {r.text}"
        if r.status_code != 200:
            raise exceptions.InterchainConnectionError(error_status)
        response = r.json()
        error_response = "The server call got an error response: {response}"
        if not isinstance(response, list):  # "fees" returns list
            if response.get("error") or response.get("errors"):
                raise exceptions.InterchainConnectionError(error_response)
        return response

    def export_as_at_rest(self) -> Dict[str, Any]:
        """Export this network to be saved in storage
        Returns:
            DTO as a dictionary to be saved
        """
        return {
            "version": "1",
            "blockchain": self.blockchain,
            "name": self.name,
            "testnet": self.testnet,
            "node_ip": self.node_ip,
            "rpc_port": self.rpc_port,
            "api_port": self.api_port,
            "private_key": self.get_private_key(),
        }

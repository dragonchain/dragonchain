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

import secp256k1
import requests
import mnemonic
from pycoin.symbols.btc import network
from binance_transaction import BnbTransaction  # bnb-tx-python module
from binance_transaction import TestBnbTransaction  # bnb-tx-python module

from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib.dto import model
from dragonchain.lib import keys
from dragonchain.lib import segwit_addr

NODE_URL = "http://binance-node.dragonchain.com"  # mainnet and testnet are the same EC2
MAINNET_RPC_PORT = 27147
MAINNET_API_PORT = 1169
TESTNET_RPC_PORT = 26657
TESTNET_API_PORT = 11699

CONFIRMATIONS_CONSIDERED_FINAL = 1  # https://docs.binance.org/faq.html#what-is-the-design-principle-of-binance-chain
BLOCK_THRESHOLD = 3  # The number of blocks that can pass by before trying to send another transaction
SEND_FEE = 37500  # transfer fee fixed at 0.000375 BNB : https://docs.binance.org/trading-spec.html#current-fees-table-on-mainnet

_log = logger.get_logger()


def new_from_user_input(user_input: Dict[str, Any]) -> "BinanceNetwork":  # noqa: C901
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
            user_input["private_key"] = base64.b64encode(secp256k1.PrivateKey().private_key).decode("ascii")
        else:
            try:
                # Check if user provided key is hex and convert if necessary
                if len(user_input["private_key"]) == 66:  # private keys in hex are 66 chars with leading 0x
                    user_input["private_key"] = user_input["private_key"][2:]  # Trim the 0x
                if len(user_input["private_key"]) == 64:  # private keys in hex are 64 chars
                    user_input["private_key"] = base64.b64encode(bytes.fromhex(user_input["private_key"])).decode("ascii")
                else:
                    try:  # is it a base64 key?  check!
                        secp256k1.PrivateKey(privkey=base64.b64decode(user_input["private_key"]), raw=True)
                    except Exception:
                        _log.warning("[BINANCE] Key not hex or base64... falling back to generating key from mnemonic.")
                        # not hex, not base64... at this point, assume key is a mnemonic string
                        seed = mnemonic.Mnemonic.to_seed(user_input["private_key"])
                        parent_wallet = network.keys.bip32_seed(seed)
                        child_wallet = parent_wallet.subkey_for_path("44'/714'/0'/0/0")
                        # convert secret exponent (private key) int to hex
                        key_hex = format(child_wallet.secret_exponent(), "x")
                        user_input["private_key"] = base64.b64encode(bytes.fromhex(key_hex)).decode("ascii")
            except Exception:
                _log.exception(f"[BINANCE] Exception thrown during key handling.  Bad key: {user_input['private_key']}")
                raise exceptions.BadRequest("Provided private key did not successfully decode into a valid key.")

        # check if user specified that node is a testnet
        if user_input.get("testnet") is None:
            user_input["testnet"] = True  # default to testnet
        # check for user-provided node address
        if not user_input.get("node_url"):
            # default to Dragonchain managed Binance node if not provided
            user_input["node_url"] = NODE_URL
            user_input["rpc_port"] = TESTNET_RPC_PORT if user_input.get("testnet") else MAINNET_RPC_PORT
            user_input["api_port"] = TESTNET_API_PORT if user_input.get("testnet") else MAINNET_API_PORT
        else:  # user specified NODE_URL; make sure they specified ports, too!
            if not user_input["rpc_port"] or not user_input["api_port"]:
                raise exceptions.BadRequest("Node URL specified, but RPC or API ports not specified.")
        # Create the actual client and check that the given node is reachable
        try:
            client = BinanceNetwork(
                name=user_input["name"],
                testnet=user_input["testnet"],
                node_url=user_input["node_url"],
                rpc_port=user_input["rpc_port"],
                api_port=user_input["api_port"],
                b64_private_key=user_input["private_key"],
            )
        except Exception as e:
            _log.exception("[BINANCE] Exception thrown during client creation.")
            raise exceptions.BadRequest(f"Client creation failed. Error: {e}")
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
            node_url=binance_network_at_rest["node_url"],
            rpc_port=binance_network_at_rest["rpc_port"],
            api_port=binance_network_at_rest["api_port"],
            b64_private_key=binance_network_at_rest["private_key"],
        )
    else:
        raise NotImplementedError(f"DTO version {dto_version} not supported for binance network")


class BinanceNetwork(model.InterchainModel):
    def __init__(self, name: str, testnet: bool, node_url: str, rpc_port: int, api_port: int, b64_private_key: str):
        self.blockchain = "binance"
        self.name = name
        self.testnet = testnet
        self.node_url = node_url
        self.rpc_port = rpc_port
        self.api_port = api_port
        self.b64_private_key = b64_private_key

        decoded_key = base64.b64decode(b64_private_key)
        priv_key = secp256k1.PrivateKey(privkey=decoded_key, raw=True)
        self.priv = priv_key
        self.pub = priv_key.pubkey

        hrp = "tbnb" if testnet else "bnb"
        self.address = segwit_addr.address_from_public_key(self.pub.serialize(compressed=True), hrp=hrp)

    def ping(self) -> None:
        """Ping this network to check if the given node is reachable and authorization is correct (raises exception if not)"""
        response_rpc = self._call_node_rpc("status", {}).json()
        response_api = self._call_node_api("tokens/BNB").json()
        if response_rpc.get("error") or response_api.get("error"):
            raise exceptions.InterchainConnectionError(f"[BINANCE] Node ping checks failed!")

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
        # txn_hash is expected to be base64, not hex:
        transaction_hash = base64.b64encode(bytes.fromhex(transaction_hash)).decode("ascii")
        response = self._call_node_rpc("tx", {"hash": transaction_hash, "prove": True}).json()
        if response.get("error") is not None:  # can't use HTTP status codes, it is a 200
            if "not found" in response["error"]["data"]:  # transaction wasn't found!
                _log.warning(f"[BINANCE] response error: {response['error']['data']}")
                raise exceptions.TransactionNotFound(f"[BINANCE] Transaction {transaction_hash} not found")
        transaction_block_number = int(response["result"]["height"])
        latest_block_number = self.get_current_block()
        _log.info(f"[BINANCE] Latest block number: {latest_block_number} | Block number of transaction: {transaction_block_number}")
        return (latest_block_number - transaction_block_number) >= CONFIRMATIONS_CONSIDERED_FINAL

    # https://docs.binance.org/api-reference/api-server.html#apiv1balanceaddresssymbol
    def check_balance(self, symbol: str = "BNB") -> int:
        """Check the balance of the address for this network
        Args:
            symbol: stock ticker symbol for token you're trying to check the balance of
        Returns:
            The amount of funds of that token in the wallet
        """
        _log.info(f"[BINANCE] Checking {symbol} balance for {self.address}")
        path = f"balances/{self.address}/{symbol}"  # params expected inside path string
        response = self._call_node_api(path)
        response_json = response.json()
        # cannot check HTTP status codes, errors will return 200 :
        if response_json.get("error") is not None:
            if "interface is nil, not types.NamedAccount" in response_json["error"]["data"] and response.status_code == 500:
                _log.warning(f"[BINANCE] Non 200 response from Binance node:")
                _log.warning(f"[BINANCE] response code: {response.status_code}")
                _log.warning(f"[BINANCE] response error: {response_json['error']['data']}")
                _log.warning("[BINANCE] This is actually expected for a zero balance address.")
                return 0  # return a zero balance
        bnb_balance = int(response_json["balance"]["free"])
        return bnb_balance

    # https://docs.binance.org/api-reference/api-server.html#apiv1fees
    def get_transaction_fee_estimate(self) -> int:
        """Calculate the transaction fee estimate for a transaction given current fee rates
        Returns:
            The amount of estimated transaction fee cost for the network
        """
        _log.info("[BINANCE] Fetching the send fee...")
        response = self._call_node_api("fees").json()
        for fee_block in response:
            if "fixed_fee_params" in fee_block:
                if fee_block["fixed_fee_params"]["msg_type"] == "send":
                    return fee_block["fixed_fee_params"]["fee"]  # fixed fee: 37500 (0.000375 BNB)
        _log.info("[BINANCE] Fetch failed; resorting to saved value for fixed fee.")
        return SEND_FEE  # SET GLOBALLY

    # https://docs.binance.org/api-reference/node-rpc.html#6110-query-block
    def get_current_block(self) -> int:
        """Get the current latest block number of the network
        Returns:
            The latest known block number on the network
        """
        # if no "height" parameter is provided,the latest block is fetched:
        response = self._call_node_rpc("block", {}).json()
        current_block = response["result"]["block"]["header"]["height"]
        return int(current_block)

    def should_retry_broadcast(self, last_sent_block: int) -> bool:
        """Check whether a new broadcast should be attempted, given a number of blocks past (for L5)
        Args:
            last_sent_block: The block when the transaction was last attempted to be sent
        Returns:
            Boolean whether a broadcast should be re-attempted
        """
        return self.get_current_block() - int(last_sent_block) > BLOCK_THRESHOLD

    def get_network_string(self) -> str:
        """Get the network string for this blockchain. This is what's included in l5 blocks or sent to matchmaking
        Returns:
            Network string
        """
        tn = "testnet: Binance-Chain-Nile"
        mn = "mainnet: Binance-Chain-Tigris"
        return f"binance {tn if self.testnet else mn}"

    def get_private_key(self) -> str:
        """Get the private key for this network
        Returns:
            string of the private key
        """
        return self.b64_private_key

    # https://docs.binance.org/api-reference/api-server.html#apiv1accountaddress
    def _fetch_account(self):
        """Fetch the account metadata for an address
        Returns:
            response containing account metadata
        """
        _log.info(f"[BINANCE] Fetching address metadata for {self.address}")
        path = f"account/{self.address}"  # params expected inside path string
        try:
            response = self._call_node_api(path)
            if response.status_code == 404:
                _log.warning("[BINANCE] 404 response from Binance node:")
                _log.warning("[BINANCE] Address not found -- likely has zero funds.")
                raise exceptions.BadRequest("[BINANCE] Error fetching metadata from 'account' endpoint.")
            return response.json()
        except exceptions.InterchainConnectionError:
            _log.warning("[BINANCE] Non 200 response from Binance node.")
            _log.warning("[BINANCE] May have been a 500 Bad Request or a 404 Not Found.")
            raise exceptions.InterchainConnectionError("[BINANCE] Error fetching metadata from 'account' endpoint.")

    def _build_transaction_msg(self, raw_transaction: Dict[str, Any]) -> Dict:
        """Build a formatted transaction for this network from the base parameters
        Args:
            amount (int): amount of token in transaction
            to_address (str): hex of the address to send to
            symbol (str, optional): the exchange symbol for the token (defaults to 'BNB')
            memo (str, optional): string of data to publish in the transaction (defaults to '')
        Returns:
            dict of the constructed transaction
        """
        amount = raw_transaction["amount"]
        if amount <= 0:
            raise exceptions.BadRequest("[BINANCE] Amount in transaction cannot be less than or equal to 0.")

        symbol = raw_transaction.get("symbol") or "BNB"
        memo = raw_transaction.get("memo") or ""

        inputs = {"address": self.address, "coins": [{"amount": amount, "denom": symbol}]}
        outputs = {"address": raw_transaction["to_address"], "coins": [{"amount": amount, "denom": symbol}]}
        response = self._fetch_account()
        transaction_data = {
            "account_number": response["account_number"],
            "sequence": response["sequence"],
            "from": self.address,
            "msgs": [{"type": "cosmos-sdk/Send", "inputs": [inputs], "outputs": [outputs]}],
            "memo": memo,
        }
        return transaction_data

    def sign_transaction(self, raw_transaction: Dict[str, Any]) -> str:
        """Sign a transaction for this network
        Args:
            amount (int): amount of token in transaction
            to_address (str): hex of the address to send to
            symbol (str, optional): the exchange symbol for the token (defaults to 'BNB')
            memo (str, optional): string of data to publish in the transaction (defaults to '')
        Returns:
            String of the signed transaction as base64
        """
        built_transaction = self._build_transaction_msg(raw_transaction)
        try:
            if self.testnet:
                tx = TestBnbTransaction.from_obj(built_transaction)
            else:  # mainnet
                tx = BnbTransaction.from_obj(built_transaction)
            _log.info(f"[BINANCE] Signing raw transaction: {tx.signing_json()}")
            mykeys = keys.DCKeys(pull_keys=False)
            mykeys.initialize(private_key_string=self.b64_private_key)
            signature = base64.b64decode(mykeys.make_binance_signature(content=tx.signing_json()))
            tx.apply_sig(signature, self.pub.serialize(compressed=True))
            signed_transaction_bytes = tx.encode()
            # signed_transaction expected to be base64, not hex:
            return base64.b64encode(signed_transaction_bytes).decode("ascii")
        except Exception as e:
            raise exceptions.BadRequest(f"[BINANCE] Error signing transaction: {e}")

    # https://docs.binance.org/api-reference/node-rpc.html#622-broadcasttxcommit
    def _publish_transaction(self, transaction_payload: str) -> str:
        """Publish a transaction to this network with a certain data payload
        Args:
            transaction_payload: The arbitrary data to send with this transaction
        Returns:
            The string of the published transaction hash
        """
        _log.info(f"[BINANCE] Publishing transaction. payload = {transaction_payload}")
        # cannot send an amount of 0 -- transaction will not be accepted!
        # send funds to yourself, avoid hardcoding a dummy recipient address
        raw_transaction = {"amount": 1, "to_address": self.address, "symbol": "BNB", "memo": transaction_payload}
        signed_tx = self.sign_transaction(raw_transaction)
        _log.info(f"[BINANCE] Sending signed transaction: {signed_tx}")
        response = self._call_node_rpc("broadcast_tx_commit", {"tx": signed_tx})
        response_json = response.json()
        # cannot check HTTP status codes, errors will return 200 :
        if response_json.get("error") is not None:
            _log.warning(f"[BINANCE] Error response from Binance node: {response_json['error']['data']}")
        return response_json["result"]["hash"]  # transaction hash

    # endpoints currently hit are:
    #     "status" (ping check)
    #     "tx" (block number check)
    #     "block" (latest block check)
    #     "broadcast_tx_commit" (submit txn)
    def _call_node_rpc(self, method: str, params: Dict[str, Any]) -> Any:
        full_address = f"{self.node_url}:{self.rpc_port}/"
        body = {"method": method, "jsonrpc": "2.0", "params": params, "id": "dontcare"}
        _log.debug(f"Binance RPC: -> {full_address} {body}")
        try:
            response = requests.post(full_address, json=body, timeout=10)
        except Exception as e:
            raise exceptions.InterchainConnectionError(f"Error sending post request to binance node: {e}")
        _log.debug(f"Binance <- {response.status_code} {response.text}")
        return response

    # endpoints currently hit are:
    #     "tokens/BNB" (ping check)
    #     "fees" (transaction fee check)
    #     "balances" (tokens in address check)
    #     "account"  (fetch account metadata)
    def _call_node_api(self, path: str) -> Any:
        full_address = f"{self.node_url}:{self.api_port}/api/v1/{path}"
        try:
            response = requests.get(full_address, timeout=10)
        except Exception as e:
            raise exceptions.InterchainConnectionError(f"Error sending get request to binance node: {e}")
        _log.debug(f"Binance <- {response.status_code} {response.text}")
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
            "node_url": self.node_url,
            "rpc_port": self.rpc_port,
            "api_port": self.api_port,
            "private_key": self.get_private_key(),
        }

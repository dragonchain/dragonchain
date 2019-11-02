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

from typing import Dict, Any, List, cast, TYPE_CHECKING

from dragonchain.lib.dto import eth
from dragonchain.lib.dto import btc
from dragonchain.lib.dto import bnb
from dragonchain.lib.dao import interchain_dao
from dragonchain import exceptions
from dragonchain import logger

_log = logger.get_logger()

if TYPE_CHECKING:
    from dragonchain.lib.dto import model


def _ethereum_client_to_user_dto_v1(eth_client: eth.EthereumNetwork) -> Dict[str, Any]:
    return {
        "version": "1",
        "blockchain": eth_client.blockchain,
        "name": eth_client.name,
        "rpc_address": eth_client.rpc_address,
        "chain_id": eth_client.chain_id,
        "address": eth_client.address,
    }


def _bitcoin_client_to_user_dto_v1(btc_client: btc.BitcoinNetwork) -> Dict[str, Any]:
    return {
        "version": "1",
        "blockchain": btc_client.blockchain,
        "name": btc_client.name,
        "rpc_address": btc_client.rpc_address,
        "testnet": btc_client.testnet,
        "address": btc_client.address,
    }


def _binance_client_to_user_dto_v1(bnb_client: bnb.BinanceNetwork) -> Dict[str, Any]:
    return {
        "version": "1",
        "blockchain": bnb_client.blockchain,
        "name": bnb_client.name,
        "node_url": bnb_client.node_url,
        "rpc_port": bnb_client.rpc_port,
        "api_port": bnb_client.api_port,
        "testnet": bnb_client.testnet,
        "address": bnb_client.address,
    }


def _get_output_dto_v1(client: "model.InterchainModel") -> Dict[str, Any]:
    if client.blockchain == "ethereum":
        return _ethereum_client_to_user_dto_v1(cast(eth.EthereumNetwork, client))
    elif client.blockchain == "bitcoin":
        return _bitcoin_client_to_user_dto_v1(cast(btc.BitcoinNetwork, client))
    elif client.blockchain == "binance":
        return _binance_client_to_user_dto_v1(cast(bnb.BinanceNetwork, client))
    else:
        raise RuntimeError(f"Unkown fetched blockchain type {client.blockchain}")


def create_bitcoin_interchain_v1(user_data: Dict[str, Any], conflict_check: bool = True) -> Dict[str, Any]:
    client = btc.new_from_user_input(user_data)
    if conflict_check and interchain_dao.does_interchain_exist("bitcoin", client.name):
        _log.error("Bitcoin network is already registered")
        raise exceptions.InterchainConflict(f"A bitcoin interchain network with the name {client.name} is already registered")
    interchain_dao.save_interchain_client(client)
    return _get_output_dto_v1(client)


def create_ethereum_interchain_v1(user_data: Dict[str, Any], conflict_check: bool = True) -> Dict[str, Any]:
    client = eth.new_from_user_input(user_data)
    if conflict_check and interchain_dao.does_interchain_exist("ethereum", client.name):
        _log.error("Ethereum network is already registered")
        raise exceptions.InterchainConflict(f"An ethereum interchain network with the name {client.name} is already registered")
    interchain_dao.save_interchain_client(client)
    return _get_output_dto_v1(client)


def create_binance_interchain_v1(user_data: Dict[str, Any], conflict_check: bool = True) -> Dict[str, Any]:
    client = bnb.new_from_user_input(user_data)
    if conflict_check and interchain_dao.does_interchain_exist("binance", client.name):
        _log.error("Binance network is already registered")
        raise exceptions.InterchainConflict(f"A binance interchain network with the name {client.name} is already registered")
    interchain_dao.save_interchain_client(client)
    return _get_output_dto_v1(client)


def update_bitcoin_interchain_v1(name: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
    # Get current client
    current_client = cast(btc.BitcoinNetwork, interchain_dao.get_interchain_client("bitcoin", name))
    # Merge user data with existing data
    client_data = {
        "version": "1",
        "name": name,
        "testnet": user_data["testnet"] if isinstance(user_data.get("testnet"), bool) else current_client.testnet,
        "private_key": user_data["private_key"] if isinstance(user_data.get("private_key"), str) else current_client.get_private_key(),
        "rpc_address": user_data["rpc_address"] if isinstance(user_data.get("rpc_address"), str) else current_client.rpc_address,
        "rpc_authorization": user_data["rpc_authorization"] if isinstance(user_data.get("rpc_authorization"), str) else current_client.authorization,
        "utxo_scan": user_data["utxo_scan"] if isinstance(user_data.get("utxo_scan"), bool) else False,
    }
    # Create and save updated client
    return create_bitcoin_interchain_v1(client_data, conflict_check=False)


def update_ethereum_interchain_v1(name: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
    # Get current client
    current_client = cast(eth.EthereumNetwork, interchain_dao.get_interchain_client("ethereum", name))
    # Merge user data with existing data
    client_data = {
        "version": "1",
        "name": name,
        "private_key": user_data["private_key"] if isinstance(user_data.get("private_key"), str) else current_client.get_private_key(),
        "rpc_address": user_data["rpc_address"] if isinstance(user_data.get("rpc_address"), str) else current_client.rpc_address,
        "chain_id": user_data["chain_id"] if isinstance(user_data.get("chain_id"), int) else current_client.chain_id,
    }
    # Create and save updated client
    return create_ethereum_interchain_v1(client_data, conflict_check=False)


def update_binance_interchain_v1(name: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
    # Get current client
    current_client = cast(bnb.BinanceNetwork, interchain_dao.get_interchain_client("binance", name))
    # Merge user data with existing data
    client_data = {
        "version": "1",
        "name": name,
        "testnet": user_data["testnet"] if isinstance(user_data.get("testnet"), bool) else current_client.testnet,
        "private_key": user_data["private_key"] if isinstance(user_data.get("private_key"), str) else current_client.get_private_key(),
        "node_url": user_data["node_url"] if isinstance(user_data.get("node_url"), str) else current_client.node_url,
        "rpc_port": user_data["rpc_port"] if isinstance(user_data.get("rpc_port"), int) else current_client.rpc_port,
        "api_port": user_data["api_port"] if isinstance(user_data.get("api_port"), int) else current_client.api_port,
    }
    # Create and save updated client
    return create_binance_interchain_v1(client_data, conflict_check=False)


def get_interchain_v1(blockchain: str, name: str) -> Dict[str, Any]:
    return _get_output_dto_v1(interchain_dao.get_interchain_client(blockchain, name))


def list_interchain_v1(blockchain: str) -> Dict[str, List[Dict[str, Any]]]:
    return {"interchains": [_get_output_dto_v1(x) for x in interchain_dao.list_interchain_clients(blockchain)]}


def delete_interchain_v1(blockchain: str, name: str) -> None:
    interchain_dao.delete_interchain_client(blockchain, name)


def set_default_interchain_v1(blockchain: str, name: str) -> Dict[str, Any]:
    return _get_output_dto_v1(interchain_dao.set_default_interchain_client(blockchain, name))


def get_default_interchain_v1() -> Dict[str, Any]:
    return _get_output_dto_v1(interchain_dao.get_default_interchain_client())


def sign_interchain_transaction_v1(blockchain: str, name: str, transaction: Dict[str, Any]) -> Dict[str, str]:
    client = interchain_dao.get_interchain_client(blockchain, name)
    # Delete the user provided version field before passing it to sign transaction
    try:
        del transaction["version"]
    except KeyError:  # If the key doesn't exist, that is fine
        pass
    return {"signed": client.sign_transaction(transaction)}


# Below methods are deprecated and exist for legacy support only. Both methods will return a 404 if not a legacy chain


def legacy_get_blockchain_addresses_v1() -> Dict[str, str]:
    return {
        "eth_mainnet": interchain_dao.get_interchain_client("ethereum", "ETH_MAINNET").address,
        "eth_ropsten": interchain_dao.get_interchain_client("ethereum", "ETH_ROPSTEN").address,
        "etc_mainnet": interchain_dao.get_interchain_client("ethereum", "ETC_MAINNET").address,
        "etc_morden": interchain_dao.get_interchain_client("ethereum", "ETC_MORDEN").address,
        "btc_mainnet": interchain_dao.get_interchain_client("bitcoin", "BTC_MAINNET").address,
        "btc_testnet3": interchain_dao.get_interchain_client("bitcoin", "BTC_TESTNET3").address,
    }


def legacy_sign_blockchain_transaction_v1(network: str, transaction: Dict[str, Any]) -> Dict[str, str]:
    if network in ["BTC_MAINNET", "BTC_TESTNET3"]:  # Check if legacy bitcoin network
        client = interchain_dao.get_interchain_client("bitcoin", network)
    else:  # Must be a legacy ethereum network
        client = interchain_dao.get_interchain_client("ethereum", network)

    return {"signed": client.sign_transaction(transaction)}

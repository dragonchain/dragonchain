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

from dragonchain.lib.dto import eth
from dragonchain.lib.dto import btc
from dragonchain.lib.dao import interchain_dao


def create_bitcoin_interchain_v1(user_data: Dict[str, Any]) -> None:
    client = btc.new_from_user_input(user_data)
    interchain_dao.save_interchain_client(client)


def create_ethereum_intercchain_v1(user_data: Dict[str, Any]) -> None:
    client = eth.new_from_user_input(user_data)
    interchain_dao.save_interchain_client(client)


# Below methods are deprecated and exist for legacy support only. Both methods will return a 404 if not a legacy chain


def get_blockchain_addresses_v1() -> Dict[str, str]:
    return {
        "eth_mainnet": interchain_dao.get_interchain_client("ethereum", "ETH_MAINNET").address,
        "eth_ropsten": interchain_dao.get_interchain_client("ethereum", "ETH_ROPSTEN").address,
        "etc_mainnet": interchain_dao.get_interchain_client("ethereum", "ETC_MAINNET").address,
        "etc_morden": interchain_dao.get_interchain_client("ethereum", "ETC_MORDEN").address,
        "btc_mainnet": interchain_dao.get_interchain_client("bitcoin", "BTC_MAINNET").address,
        "btc_testnet3": interchain_dao.get_interchain_client("bitcoin", "BTC_TESTNET3").address,
    }


def sign_blockchain_transaction_v1(network: str, transaction: Dict[str, Any]) -> Dict[str, str]:
    if network in ["BTC_MAINNET", "BTC_TESTNET3"]:  # Check if legacy bitcoin network
        client = interchain_dao.get_interchain_client("bitcoin", network)
    else:  # Must be a legacy ethereum network
        client = interchain_dao.get_interchain_client("ethereum", network)

    return {"signed": client.sign_transaction(transaction)}

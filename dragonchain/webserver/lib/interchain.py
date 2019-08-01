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

from dragonchain.lib.interfaces import interchain
from dragonchain.lib.interfaces.networks import eth
from dragonchain.lib.interfaces.networks import btc


def get_blockchain_addresses_v1() -> Dict[str, str]:
    return {
        "eth_mainnet": eth.load_address("ETH_MAINNET")[0],
        "eth_ropsten": eth.load_address("ETH_ROPSTEN")[0],
        "etc_mainnet": eth.load_address("ETC_MAINNET")[0],
        "etc_morden": eth.load_address("ETC_MORDEN")[0],
        "btc_mainnet": btc.load_address("BTC_MAINNET")[0],
        "btc_testnet3": btc.load_address("BTC_TESTNET3")[0],
    }


def sign_blockchain_transaction_v1(network: str, transaction: Dict[str, Any]) -> Dict[str, str]:
    network_interface = interchain.InterchainInterface(network)
    signed = network_interface.sign_transaction(transaction)
    return {"signed": signed}

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

from typing import Union, Dict, Any

PUBLISH_PREFIX = "DC-L5"


class InterchainInterface(object):
    def __init__(self, network: str):
        self.network = network

        # Import the correct interchain client
        if self.network in ["BTC_MAINNET", "BTC_TESTNET3"]:
            from dragonchain.lib.interfaces.networks.btc import BTCClient as Client
        elif self.network in ["ETH_MAINNET", "ETH_ROPSTEN", "ETC_MAINNET", "ETC_MORDEN"]:
            from dragonchain.lib.interfaces.networks.eth import ETHClient as Client  # noqa: T484 this is intentional
        else:
            raise RuntimeError(f"Invalid interchain network provided: {self.network}")

        self.client = Client(self.network)

    def sign_transaction(self, raw_transaction: Dict[str, Any]) -> str:
        return self.client.sign_transaction(raw_transaction)

    def publish_to_public_network(self, l5_block_hash: str) -> Any:
        transaction_payload = f"{PUBLISH_PREFIX}:{l5_block_hash}"
        transaction_hash = self.client.publish_transaction(transaction_payload)
        return transaction_hash

    def is_transaction_confirmed(self, transaction_hash: str) -> Union[bool, str]:
        """
        1. Check if approx time has elapsed to warrant a check.
        2. If so, get the confirmation_info for the specified block(s)
        3. If confirmation meets criteria, return transaction_id || block_id. else return false.
        """
        return self.client.is_transaction_confirmed(transaction_hash)

    def check_balance(self) -> int:
        return self.client.check_address_balance()

    def get_transaction_fee_estimate(self) -> int:
        return self.client.get_transaction_fee_estimate()

    def get_current_block(self) -> Any:
        return self.client.get_current_block()

    def get_retry_threshold(self) -> int:
        return self.client.get_retry_threshold()

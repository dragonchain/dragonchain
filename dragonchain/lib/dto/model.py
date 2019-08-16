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

from typing import Set, Dict, Any

# TODO With python 3.8, implement protocols (static duck typing) for models


class Model(object):
    def export_as_search_index(self) -> dict:
        """Abstract Method"""
        raise NotImplementedError("This is an abstract method")

    def export_as_at_rest(self) -> dict:
        """Abstract Method"""
        raise NotImplementedError("This is an abstract method")


class BlockModel(Model):
    block_id: str
    dc_id: str
    proof: str

    def get_associated_l1_dcid(self) -> str:
        """Abstract Method"""
        raise NotImplementedError("This is an abstract method")

    def get_associated_l1_block_id(self) -> Set[str]:
        """Abstract Method"""
        raise NotImplementedError("This is an abstract method")


class InterchainModel(Model):
    name: str

    def sign_transaction(self, raw_transaction: Dict[str, Any]) -> str:
        """Sign a transaction for this network
        Args:
            raw_transaction: Transaction dictionary for this particular blockchain type
        Returns:
            String representation of the signed transaction
        """
        raise NotImplementedError("This is an abstract method")

    def publish_l5_hash_to_public_network(self, l5_block_hash: str) -> str:
        """Publish an l5 block hash to this network
        Args:
            l5_block_hash: The string of the l5 block hash to publish
        Returns:
            String of the transaction hash (or equivalent) for the posted transaction
        """
        return self._publish_transaction(f"DC-L5:{l5_block_hash}")

    def is_transaction_confirmed(self, transaction_hash: str) -> bool:
        """Check if a transaction is considered confirmed
        Args:
            transaction_hash: The hash (or equivalent, i.e. id) of the transaction to check
        Returns:
            Boolean if the transaction has receieved enough confirmations to be considered confirmed
        Raises:
            exceptions.RPCTransactionNotFound: When the transaction could not be found (may have been dropped)
        """
        raise NotImplementedError("This is an abstract method")

    def check_balance(self) -> int:
        """Check the balance of the address for this network
        Returns:
            The amount of funds in this network's wallet
        """
        raise NotImplementedError("This is an abstract method")

    def get_transaction_fee_estimate(self) -> int:
        """Calculate the transaction fee estimate for a transaction given current fee rates
        Returns:
            The amount of estimated transaction fee cost for the network
        """
        raise NotImplementedError("This is an abstract method")

    def get_current_block(self) -> int:
        """Get the current latest block number of the network
        Returns:
            The latest known block number on the network
        """
        raise NotImplementedError("This is an abstract method")

    def should_retry_broadcast(self, last_sent_block: int) -> bool:
        """Check whether a new broadcast should be attempted, given a number of blocks past (for L5)
        Args:
            last_sent_block: The block when the transaction was last attempted to be sent
        Returns:
            Boolean whether a broadcast should be re-attempted
        """
        raise NotImplementedError("This is an abstract method")

    def _publish_transaction(self, payload: str) -> str:
        """Publish a transaction to this network with a certain data payload
        Args:
            transaction_payload: The arbitrary data to send with this transaction
        Returns:
            The string of the published transaction hash (or equivalent)
        """
        raise NotImplementedError("This is an abstract method")

"""
Copyright 2016 Disney Connected and Advanced Technologies

Licensed under the Apache License, Version 2.0 (the "Apache License")
with the following modification; you may not use this file except in
compliance with the Apache License and the following modification to it:
Section 6. Trademarks. is deleted and replaced with:

     6. Trademarks. This License does not grant permission to use the trade
        names, trademarks, service marks, or product names of the Licensor
        and its affiliates, except as required to comply with Section 4(c) of
        the License and to reproduce the content of the NOTICE file.

You may obtain a copy of the Apache License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the Apache License with the above modification is
distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied. See the Apache License for the specific
language governing permissions and limitations under the Apache License.
"""

__author__ = "Joe Roets, Brandon Kite, Dylan Yelton, Michael Bachtel"
__copyright__ = "Copyright 2016, Disney Connected and Advanced Technologies"
__license__ = "Apache"
__version__ = "2.0"
__maintainer__ = "Joe Roets"
__email__ = "joe@dragonchain.org"

from hashlib import sha256
from struct import pack
import json


class IProof:
    """
    Abstracts the concept of 'proof'. It has to be serializable (json) in order to
    persisted as part of the block.
    """
    def to_JSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                              sort_keys=True, indent=4)

class IProofProvider:
    """
    Abstracts the mechanism of getting a proof and validate it.
    """
    def create_proof(self, raw):
        pass

    def is_enough(self, proof):
        """
        Checks if the proof is 'hard' enough to be considered valid
        Args:
            proof: the proof instance to be validated

        Returns:
            boolean value True if the proof is enough; otherwise False
        """
        pass

    def state(self):
        pass


class Sha256Proof(IProof):
    """
    Represents a proof of work using simple sha256 hashing algorithm (bitcoin uses double, sha256(sha256()))
    """
    def __init__(self, work, nonce, target):
        """

        Args:
            work:   the hash value that found as part of the PoW
            nonce:  the 'nonce' value found as part of the mining process
            target: the hash value used as upper bound for the 'work' hash
        """
        self.hash = work
        self.nonce = nonce
        self.target= target

    def is_enough(self):
        """
        Checks if the mined proof value is less than the target hash

        Returns:
            boolean value True if the proof less than target; otherwise False
        """
        return self.hash < self.target

    def _calculate(self, raw):
        """
        Increments the 'nonce' value and performs the hashing
        Args:
            raw: the data we want to mine. Typically, a block.

        """
        self.hash = int(sha256(pack('>Q', self.nonce) + raw).hexdigest(), base=16)
        self.nonce += 1


TWO_EXP_256 = 2 ** 256 - 1


class ProofOfWork256Provider(IProofProvider):
    """
    Implements the Proof of Work mining process using SHA256 as hashing algorithm
    """
    def __init__(self, work=TWO_EXP_256, nonce=0, target=TWO_EXP_256):
        """
        Initializes the miner with the initial values
        Args:
            work:   the initial work done (minimun work by default)
            nonce:  the initial nonce value (given we scan the sequentially the field, zero is the best to use)
            target: the initail target value (by default we want no difficulty)
        """
        self.proof = Sha256Proof(work, nonce, target)

    def create_proof(self, raw):
        """
        Searches a proof with enough work (a valid one)
        Args:
            raw: the data we want to mine. Typically, a block.

        Returns:
            the found proof of work proof.
        """
        self.proof._calculate(raw)
        while not self.proof.is_enough():
            self.proof._calculate(raw)
        return self.proof



class CoinsBurnedProof(IProof):
    """
    Represents a proof of burn. That means that it contains the data required
    for proving that a coin was burned as part of a mining process.
    """
    # an wellknown address for burning coins
    burning_address = "1BitcoinToTheMoonSuchProfitvZUEsk"
    def __init__(self, spent_tx_output):
        """
        Initializes the proof with the spent tx output that was burned
        Args:
            spent_tx_output: the burned tx output
        """
        self.spent_tx_output = spent_tx_output
        #.....
        # .....

    def is_enough(self):
        """
        Checks if the burned coin is sent to the burning address.
        Checks if the burned coin is 'bigger enough'.

        Returns:
            boolean value True if the proof less than target; otherwise False
        """
        if self.spent_tx_output.address != self.burning_address:
            return False
        if self.spent_tx_output.amount < self.get_burning_amount_for_block(self.spent_tx_output.tx.block):
            return False
        # .....
        # more consensus validations here
        # .....

        return True



class CoinsBurnedProofProvider(IProofProvider):
    """
    Implements the Proof of Burn mining process
    """
    def __init__(self, spent_tx_output):
        self.proof = CoinsBurnedProof(spent_tx_output)

    def create_proof(self, raw):
        # get an utxo with 'amount' enough and send it to the CoinsBurnedProof.burning_address
        # the amount can be based on whatever consensus rules we set
        return self.proof



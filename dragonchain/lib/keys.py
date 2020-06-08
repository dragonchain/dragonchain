# Copyright 2020 Dragonchain, Inc.
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

import os
import enum
import base64
from typing import cast, Tuple, Optional, TYPE_CHECKING

import base58
import secp256k1

from dragonchain.lib import crypto
from dragonchain.lib import matchmaking
from dragonchain.lib.interfaces import secrets
from dragonchain import exceptions

if TYPE_CHECKING:
    from dragonchain.lib.dto import model
    from dragonchain.lib.dto import transaction_model
    from dragonchain.lib.dto import l1_block_model  # noqa: F401
    from dragonchain.lib.dto import l2_block_model  # noqa: F401
    from dragonchain.lib.dto import l3_block_model  # noqa: F401
    from dragonchain.lib.dto import l4_block_model  # noqa: F401
    from dragonchain.lib.dto import l5_block_model  # noqa: F401

LEVEL = os.environ["LEVEL"]
PROOF_SCHEME = os.environ["PROOF_SCHEME"]
HASH = os.environ["HASH"]
ENCRYPTION = os.environ["ENCRYPTION"]


_my_keys = None
_public_id = ""


def get_public_id() -> str:
    """Memo-ized retrieval/calculation for the chain's derived public id
    Returns:
        String of the chain's public_id
    """
    global _public_id
    if not _public_id:
        keys = get_my_keys()
        if not keys.priv:
            raise RuntimeError("My keys doesn't have private key set")
        _public_id = crypto.calculate_public_id(keys.priv.pubkey.serialize())
    return _public_id


def get_my_keys() -> "DCKeys":
    """
    Memo-ized retrieval for the keys owned by this chain
    """
    global _my_keys
    if _my_keys is None:
        _my_keys = DCKeys(pull_keys=False).initialize(
            level=int(LEVEL), scheme=PROOF_SCHEME, private_key_string=secrets.get_dc_secret("private-key"), hash_type=HASH, encryption=ENCRYPTION
        )
    return _my_keys


class SupportedSchemes(enum.Enum):
    trust = 1
    work = 2


class DCKeys(object):
    """
    Class for holding keys to sign/verify transactions/blocks of individual dragonchains
    """

    def __init__(self, dc_id: str = "", pull_keys: bool = True, override_level: Optional[str] = None):
        """Constructor to retrieve and initialize keys for a dragonchain
        Args:
            dc_id: string of the dragonchain id to initialize the keys (defaults to self)
            pull_keys: boolean whether or not to pull key info from storage (if own keys) or matchmaking (if other chain keys) on initialization
        """
        if pull_keys:
            try:
                identity = matchmaking.get_registration(dc_id)
            except exceptions.NotFound:
                identity = {}
            self.initialize(
                level=int(identity.get("level") or override_level or 1),
                scheme=identity.get("proofScheme") or "trust",
                public_key_string=dc_id,
                hash_type=identity.get("hashAlgo") or "blake2b",
                encryption=identity.get("encryptionAlgo") or "secp256k1",
            )

    def initialize(
        self,
        level: int = 1,
        scheme: str = "trust",
        private_key_string: Optional[str] = None,
        public_key_string: Optional[str] = None,
        hash_type: str = "blake2b",
        encryption: str = "secp256k1",
    ) -> "DCKeys":
        """Initializes the internal state of the keys object with local data that is passed in
        Args:
            level: integer of the dragonchain level that owns these key(s)
            private_key_string: base64 encoded private key string, setting this will automatically derive the public key
            public_key_string: base64 encoded public key string, only used for verification functions
        Returns:
            Self (initialized DCKeys instance)
        """
        self.priv = None
        self.pub = None
        self.set_scheme(scheme)
        self.set_level(level)
        self.set_hash(hash_type)
        self.set_encryption(encryption)
        if public_key_string is not None:
            self.set_public_key(public_key_string)
        if private_key_string is not None:
            self.set_private_key(private_key_string)
        return self

    def set_scheme(self, scheme: str) -> None:
        """Sets the dragonchain scheme for this instantiation of the class
        Args:
            scheme: string of a valid proof scheme
        Raises:
            exceptions.NotImplementedError when invalid scheme
        """
        scheme = scheme.lower()
        if scheme == "trust":
            self.scheme = SupportedSchemes.trust
        elif scheme == "work":
            self.scheme = SupportedSchemes.work
        else:
            raise NotImplementedError("Unimplemented or invalid scheme type")

    def set_level(self, level: int) -> None:
        """Sets the dragonchain level for this instantiation of the class
        Args:
            level: int between 1 and 5
        Raises:
            exceptions.TypeError when invalid level
        """
        if not isinstance(level, int) or level > 5 or level < 1:
            raise TypeError("Level was not a valid int")
        self.level = level

    def set_encryption(self, encryption_type: str) -> None:
        """Sets the encryption type for this instanation of the class
        Args:
            encryption_type: sring fo the encryption type (eg secp256k1)
        Raises:
            NotImplementedError when invalid encryption_type
        """
        # Modify this statement as support for other encryption algorithms change in crypto.py
        if encryption_type == "secp256k1":
            self.encryption = crypto.SupportedEncryption.secp256k1
        else:
            raise NotImplementedError(f"Encryption type {encryption_type} not implemented")

    def set_hash(self, hash_type: str) -> None:
        """Sets the hash type for this instantiation of the class
        Args:
            hash_type: string of the hash type (eg 'blake2b')
        Raises:
            NotImplementedError when invalid hash_type
        """
        # Modify this statement as support for other hashing algorithms change in crypto.py
        if hash_type == "blake2b":
            self.hash = crypto.SupportedHashes.blake2b
        elif hash_type == "sha256":
            self.hash = crypto.SupportedHashes.sha256
        elif hash_type == "sha3_256":
            self.hash = crypto.SupportedHashes.sha3_256
        else:
            raise NotImplementedError(f"Hash type {hash_type} not implemented")

    def set_private_key(self, private_key_string: str) -> None:
        """Sets the private (and derives the public) key for this instantiation of the class
        Note: This must be called AFTER self.encryption (set_encryption) is already set
        Args:
            private_key_string: base64 encoded private key string
        Raises:
            NotImplementedError when invalid encryption type on self
        """
        decoded_key = base64.b64decode(private_key_string)
        # Modify this statement as support for other encryption algorithms change
        if self.encryption == crypto.SupportedEncryption.secp256k1:
            priv_key = secp256k1.PrivateKey(privkey=decoded_key, raw=True)
            self.priv = priv_key
            self.pub = priv_key.pubkey
        else:
            raise NotImplementedError("Encryption algorithm not implemented")

    def set_public_key(self, public_key_string: str) -> None:
        """Sets the public key (and clears the private key) for this instantiation of the class
        Note: This must be called AFTER self.encryption (set_encryption) is already set
        Args:
            public_key_string: base58 encoded public key string (public dragonchain id)
        Raises:
            NotImplementedError when invalid encryption_type
        """
        decoded_key = base58.b58decode(public_key_string)
        # Modify this statement as support for other encryption algorithms change
        if self.encryption == crypto.SupportedEncryption.secp256k1:
            self.pub = secp256k1.PublicKey(pubkey=decoded_key, raw=True)
        else:
            raise NotImplementedError("Encryption algorithm not implemented")

        self.priv = None

    def check_signature(self, content: bytes, signature: str, hash_type: Optional[crypto.SupportedHashes] = None) -> bool:
        """Check a generic signature for some bytes of data with these keys
        Args:
            content: content bytes that were signed
            signature: Base64 encoded signature (as a string)
            hash_type: SupportedHashes enum of hash type used to check signature (defaults to keys hash type if not provided)
        Returns:
            boolean if signature is valid or not
        """
        if hash_type is None:
            hash_type = self.hash
        return crypto.check_generic_signature(self.encryption, hash_type, self.pub, content, base64.b64decode(signature))

    def make_signature(self, content: bytes, hash_type: Optional[crypto.SupportedHashes] = None) -> str:
        """Make a generic signature for some bytes of data
        Args:
            content: content bytes to sign
            hash_type: Hash type to use for this signature. Defaults to chain's hash type if not explicitly provided
        Returns:
            base64 encoded signature string
        Raises:
            RuntimeError when no private key is set
        """
        if self.priv is None:
            raise RuntimeError("No private key has been set for signing")
        if hash_type is None:
            hash_type = self.hash
        return crypto.make_generic_signature(self.encryption, hash_type, self.priv, content)

    def make_binance_signature(self, content: bytes) -> str:
        """Make a generic signature for some bytes of data
        Args:
            content: json bytes to sign
        Returns:
            base64 encoded signature string
        Raises:
            RuntimeError when no private key is set
        """
        if self.priv is None:
            raise RuntimeError("No private key has been set for signing")
        message = crypto.hash_bytes(hash_type=crypto.SupportedHashes.sha256, bytes_param=content)
        return crypto.encrypt_secp256k1_message_compact(self.priv, message)

    def sign_block(self, signable_block: "model.BlockModel") -> str:
        """Sign a block with this class' keys
        Args:
            block: BlockModel to sign
        Returns:
            Base64 encoded string of the block signature
        Raises:
            exceptions.InvalidNodeLevel when invalid level on self
            RuntimeError when no private key is set on self
        """
        if self.priv is None:
            raise RuntimeError("No private key has been set for signing")
        if self.level == 1:
            return crypto.sign_l1_block(self.hash, self.encryption, self.priv, signable_block)
        elif self.level == 2:
            return crypto.sign_l2_block(self.hash, self.encryption, self.priv, signable_block)
        elif self.level == 3:
            return crypto.sign_l3_block(self.hash, self.encryption, self.priv, signable_block)
        elif self.level == 4:
            return crypto.sign_l4_block(self.hash, self.encryption, self.priv, signable_block)
        elif self.level == 5:
            return crypto.sign_l5_block(self.hash, self.encryption, self.priv, signable_block)
        else:
            raise exceptions.InvalidNodeLevel(f"Node level {self.level} not implemented yet")

    def hash_l5_for_public_broadcast(self, signable_block: "l5_block_model.L5BlockModel") -> str:
        """Hash a block with this class' keys
        Args:
            block: BlockModel to sign
        Returns:
            Base64 encoded string of the block hash
        """
        return base64.b64encode(crypto.hash_l5_block(self.hash, signable_block)).decode("ascii")

    def pow_block(self, signable_block: "model.BlockModel") -> Tuple[str, int]:
        """Do proof of work on a block
        Args:
            block: BlockModel to do proof of work on
        Returns:
            Tuple where index 0 is a Base64 encoded string of the generated hash and index 1 is the nonce
        Raises:
            exceptions.InvalidNodeLevel when invalid level on self
        """
        if self.level == 1:
            return crypto.pow_l1_block(self.hash, cast("l1_block_model.L1BlockModel", signable_block))
        elif self.level == 2:
            return crypto.pow_l2_block(self.hash, cast("l2_block_model.L2BlockModel", signable_block))
        elif self.level == 3:
            return crypto.pow_l3_block(self.hash, cast("l3_block_model.L3BlockModel", signable_block))
        elif self.level == 4:
            return crypto.pow_l4_block(self.hash, cast("l4_block_model.L4BlockModel", signable_block))
        else:
            raise exceptions.InvalidNodeLevel(f"Node level {self.level} not implemented yet")

    def verify_block(self, block: "model.BlockModel") -> bool:  # noqa: C901
        """Verify a block with this class' keys
        Args:
            block: BlockModel to verify
        Returns:
            Boolean if valid block (according to these keys)
        Raises:
            NotImplementedError when invalid scheme on self
        """
        if self.scheme == SupportedSchemes.trust and self.pub is None:
            RuntimeError("No public key has been set for verifying block signature")
        if self.level == 1:
            if self.scheme == SupportedSchemes.trust:
                return crypto.verify_l1_block_trust(self.hash, self.encryption, self.pub, cast("l1_block_model.L1BlockModel", block))
            elif self.scheme == SupportedSchemes.work:
                return crypto.verify_l1_block_pow(self.hash, cast("l1_block_model.L1BlockModel", block))
            else:
                raise NotImplementedError(f"Proof scheme {self.scheme} not implemented")
        elif self.level == 2:
            if self.scheme == SupportedSchemes.trust:
                return crypto.verify_l2_block_trust(self.hash, self.encryption, self.pub, cast("l2_block_model.L2BlockModel", block))
            elif self.scheme == SupportedSchemes.work:
                return crypto.verify_l2_block_pow(self.hash, cast("l2_block_model.L2BlockModel", block))
            else:
                raise NotImplementedError(f"Proof scheme {self.scheme} not implemented")
        elif self.level == 3:
            if self.scheme == SupportedSchemes.trust:
                return crypto.verify_l3_block_trust(self.hash, self.encryption, self.pub, cast("l3_block_model.L3BlockModel", block))
            elif self.scheme == SupportedSchemes.work:
                return crypto.verify_l3_block_pow(self.hash, cast("l3_block_model.L3BlockModel", block))
            else:
                raise NotImplementedError(f"Proof scheme {self.scheme} not implemented")
        elif self.level == 4:
            if self.scheme == SupportedSchemes.trust:
                return crypto.verify_l4_block_trust(self.hash, self.encryption, self.pub, cast("l4_block_model.L4BlockModel", block))
            elif self.scheme == SupportedSchemes.work:
                return crypto.verify_l4_block_pow(self.hash, cast("l4_block_model.L4BlockModel", block))
            else:
                raise NotImplementedError(f"Proof scheme {self.scheme} not implemented")
        elif self.level == 5:
            if self.scheme == SupportedSchemes.trust:
                return crypto.verify_l5_block_trust(self.hash, self.encryption, self.pub, cast("l5_block_model.L5BlockModel", block))
            else:
                raise NotImplementedError(f"Proof scheme {self.scheme} not implemented")
        else:
            raise exceptions.InvalidNodeLevel(f"Node level {self.level} nonexistent")

    def sign_transaction(self, signable_tx: "transaction_model.TransactionModel") -> Tuple[str, str]:
        """Sign a transaction
        Args:
            signable_tx: TransactionModel to sign
        Returns:
            Tuple of strings where index 0 is the base64 encoded full hash and index 1 is the base64 encoded stripped signature
        Raises:
            exceptions.InvalidNodeLevel when self is not level 1
            RuntimeError when no private key is set on self
        """
        if self.level != 1:
            raise exceptions.InvalidNodeLevel("Transactions only exist on level 1 nodes")
        if self.priv is None:
            raise RuntimeError("No private key has been set for signing")

        return crypto.sign_transaction(self.hash, self.encryption, self.priv, signable_tx)

    def verify_stripped_transaction(self, stripped_tx: "transaction_model.TransactionModel") -> bool:
        """Verify a stripped signature on a transaction
        Args:
            stripped_tx: TransactionModel to verify (just the stripped signature)
        Returns:
            Boolean if valid signed transaction
        Raises:
            exceptions.InvalidNodeLevel when self is not level 1
            RuntimeError when no public key is set on self
        """
        if self.level != 1:
            raise exceptions.InvalidNodeLevel("Transactions only exist on level 1 nodes")
        if self.pub is None:
            raise RuntimeError("No public key has been set for verifying")

        return crypto.verify_stripped_transaction(self.hash, self.encryption, self.pub, stripped_tx)

    def verify_full_transaction(self, full_tx: "transaction_model.TransactionModel") -> bool:
        """Verify a full transaction
        Args:
            full_tx: TransactionModel to verify
        Returns:
            Boolean if valid signed and hashed transaction
        Raises:
            exceptions.InvalidNodeLevel when self is not level 1
            RuntimeError when no public key is set on self
        """
        if self.level != 1:
            raise exceptions.InvalidNodeLevel("Transactions only exist on level 1 nodes")
        if self.pub is None:
            raise RuntimeError("No public key has been set for verifying")

        return crypto.verify_full_transaction(self.hash, self.encryption, self.pub, full_tx)

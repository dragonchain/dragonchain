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

import hmac
import hashlib
import base64
import enum
from typing import Tuple, Callable, Any, TYPE_CHECKING, Union

import base58

if TYPE_CHECKING:
    from secp256k1 import PrivateKey, PublicKey  # noqa: F401
    from dragonchain.lib.dto import transaction_model
    from dragonchain.lib.dto import l1_block_model
    from dragonchain.lib.dto import l2_block_model
    from dragonchain.lib.dto import l3_block_model
    from dragonchain.lib.dto import l4_block_model
    from dragonchain.lib.dto import l5_block_model

# Define order that headers get hashed in
tx_hash_order = ["txn_id", "txn_type", "dc_id", "block_id", "tag", "invoker", "timestamp"]
l1_block_hash_order = ["dc_id", "block_id", "timestamp", "prev_proof", "prev_id"]
l2_block_hash_order = ["dc_id", "block_id", "timestamp", "prev_proof", "l1_dc_id", "l1_block_id", "l1_proof"]
l3_block_hash_order = ["dc_id", "block_id", "timestamp", "prev_proof", "l1_dc_id", "l1_block_id", "l1_proof", "ddss", "l2_count"]
l4_block_hash_order = ["dc_id", "block_id", "timestamp", "prev_proof", "l1_dc_id", "l1_block_id", "l1_proof"]
l4_block_validation_hash_order = ["l3_dc_id", "l3_block_id", "l3_proof"]
l5_block_hash_order = ["dc_id", "block_id", "timestamp", "prev_proof"]
l5_block_validation_hash_order = ["dc_id", "block_id", "timestamp", "l1_dc_id", "l1_block_id", "l1_proof", "prev_proof"]


class SupportedHashes(enum.Enum):
    blake2b = 1
    sha256 = 2
    sha3_256 = 3


class SupportedEncryption(enum.Enum):
    secp256k1 = 1


def int_to_unsigned_bytes(num: int) -> bytes:
    """Create a 64 bit unsigned byte representation of a positive integer (for nonce hashing purposes)
    Args:
        num: A positive (<64 bit) integer
    Returns:
        byte object representation of number
    """
    return num.to_bytes(8, byteorder="big", signed=False)


def get_hash_obj(hash_type: SupportedHashes) -> Any:  # Unfortunately there isn't a type/protocol for the hashlib hash duck type
    """Create a hash object that supports .update and .digest
    Args:
        hash_type: SupportedHashes enum type
    Returns:
        hash object
    Raises:
        NotImplementedError: Invalid SupportedHash provided
    """
    if hash_type == SupportedHashes.blake2b:
        return hashlib.blake2b(digest_size=32)
    elif hash_type == SupportedHashes.sha256:
        return hashlib.sha256()
    elif hash_type == SupportedHashes.sha3_256:
        return hashlib.sha3_256()
    else:
        raise NotImplementedError("Unsupported hash type")


def get_hash_method(hash_type: SupportedHashes) -> Callable:
    """Return a hash method that supports the hashlib .new function
    Args:
        hash_type: SupportedHashes enum type
    Returns:
        hash method
    Raises:
        NotImplementedError: Invalid SupportedHash provided
    """
    if hash_type == SupportedHashes.blake2b:
        return hashlib.blake2b
    elif hash_type == SupportedHashes.sha256:
        return hashlib.sha256
    elif hash_type == SupportedHashes.sha3_256:
        return hashlib.sha3_256
    else:
        raise NotImplementedError("Unsupported hash type")


def hash_bytes(hash_type: SupportedHashes, bytes_param: bytes) -> bytes:
    """Hash arbitrary bytes using a supported algo of your choice.
    Args:
        hash_type: SupportedHashes enum type
        bytes_param: bytes to be hashed
    Returns:
        hashed bytes
    """
    hasher = get_hash_obj(hash_type)
    hasher.update(bytes_param)
    return hasher.digest()


def create_hmac(hash_type: SupportedHashes, secret: str, message: str) -> bytes:
    """Create an hmac from a given hash type, secret, and message
    Args:
        hash_type: SupportedHashes enum type
        secret: the (utf-8 encodable) secret string to be used to generate the hmac
        message: A utf-8 encodable string to use as the hmac message
    Returns:
        Bytes for the generated hmac
    """
    hash_method = get_hash_method(hash_type)
    hashed = hmac.new(key=secret.encode("utf-8"), msg=message.encode("utf-8"), digestmod=hash_method)
    return hashed.digest()


def compare_hmac(hash_type: SupportedHashes, original_hmac: bytes, secret: str, message: str) -> bool:
    """Compare a provided base64 encoded hmac string with a generated hmac from the provided secret/message
    Args:
        hash_type: SupportedHashes enum type
        original_hmac: hmac bytes to compare
        secret: the (utf-8 encodable) secret string to be used to generate the hmac to compare
        message: A utf-8 encodable string to use with the hmac generation
    Returns:
        Boolean if hmac matches or not
    """
    return hmac.compare_digest(original_hmac, create_hmac(hash_type, secret, message))


def calculate_public_id(public_key: bytes) -> str:
    """Calculate the public id for a given public key
    Args:
        public_key: bytes of the public key to convert into a public_id
    Returns:
        String of the calculated public_id
    """
    return base58.b58encode(public_key).decode("ascii")


def validate_public_id(public_key: bytes, public_id: str) -> bool:
    """Validate that a public key matches a public id
    Note: This function is not safe from timing attacks, so don't use this when safety is required
    Args:
        public_key: bytes of the public key to check
        public_id: string of the public id to check
    Returns:
        Boolean true if key and id match, false if not
    """
    return calculate_public_id(public_key) == public_id


def hash_full_transaction(hash_type: SupportedHashes, transaction: "transaction_model.TransactionModel") -> bytes:
    """Hash a transaction
    Args:
        hash_type: SupportedHashes enum type
        transaction: TransactionModel with appropriate data to hash
    Returns:
        Bytes for the hash of the full transaction
    """
    # Setting up hash object
    full_hash = get_hash_obj(hash_type)
    # Hash data
    for curr in tx_hash_order:
        full_hash.update(transaction.__dict__[curr].encode("utf-8"))
    # Add payload to full hash then digest
    full_hash.update(transaction.payload.encode("utf-8"))
    return full_hash.digest()


def hash_stripped_transaction(hash_type: SupportedHashes, full_hash_bytes: bytes, transaction: "transaction_model.TransactionModel") -> bytes:
    """Hash a stripped transaction
    Args:
        hash_type: SupportedHashes enum type
        full_hash: Bytes of the fullhash for the transaction
        transaction: TransactionModel with appropriate data to hash
    Returns:
        Bytes for the hash of the stripped transaction
    """
    # Setting up hash object
    stripped_hash = get_hash_obj(hash_type)
    # Hash data
    for curr in tx_hash_order:
        stripped_hash.update(transaction.__dict__[curr].encode("utf-8"))
    # Add full hash to stripped hash then digest (for signature message)
    stripped_hash.update(full_hash_bytes)
    return stripped_hash.digest()


def hash_l1_block(hash_type: SupportedHashes, block: "l1_block_model.L1BlockModel", nonce: int = 0) -> bytes:
    """Hash an l1 block
    Args:
        hash_type: SupportedHashes enum type
        block: L1BlockModel with appropriate data to hash
        nonce: (OPTIONAL) A nonce in the form of a positive integer
    Returns:
        Bytes for the hash of the block
    """
    # Get hash object
    proof_hash = get_hash_obj(hash_type)
    # Create hash for message signing
    for curr in l1_block_hash_order:
        proof_hash.update(block.__dict__[curr].encode("utf-8"))
    for tx in block.stripped_transactions:
        proof_hash.update(tx.encode("utf-8"))
    if nonce:
        proof_hash.update(int_to_unsigned_bytes(nonce))
    return proof_hash.digest()


def hash_l2_block(hash_type: SupportedHashes, block: "l2_block_model.L2BlockModel", nonce: int = 0) -> bytes:
    """Hash an l2 block
    Args:
        hash_type: SupportedHashes enum type
        block: L2BlockModel with appropriate data to hash
        nonce: (OPTIONAL) A nonce in the form of a positive integer
    Returns:
        Bytes for the hash of the block
    """
    # Get hash object
    proof_hash = get_hash_obj(hash_type)
    # Create hash for message signing
    for curr in l2_block_hash_order:
        proof_hash.update(block.__dict__[curr].encode("utf-8"))
    proof_hash.update(block.validations_str.encode("utf-8"))
    if nonce:
        proof_hash.update(int_to_unsigned_bytes(nonce))
    return proof_hash.digest()


def hash_l3_block(hash_type: SupportedHashes, block: "l3_block_model.L3BlockModel", nonce: int = 0) -> bytes:
    """Hash an l3 block
    Args:
        hash_type: SupportedHashes enum type
        block: L3BlockModel with appropriate data to hash
        nonce: (OPTIONAL) A nonce in the form of a positive integer
    Returns:
        Bytes for the hash of the block
    """
    # Get hash object
    proof_hash = get_hash_obj(hash_type)
    # Create hash for message signing
    for curr in l3_block_hash_order:
        proof_hash.update(block.__dict__[curr].encode("utf-8"))
    for region in block.regions:
        proof_hash.update(region.encode("utf-8"))
    for cloud in block.clouds:
        proof_hash.update(cloud.encode("utf-8"))
    if nonce:
        proof_hash.update(int_to_unsigned_bytes(nonce))
    if block.l2_proofs is not None:
        for proof in block.l2_proofs:
            proof_hash.update(proof["dc_id"].encode("utf-8"))
            proof_hash.update(proof["block_id"].encode("utf-8"))
            proof_hash.update(proof["proof"].encode("utf-8"))
    return proof_hash.digest()


def hash_l4_block(hash_type: SupportedHashes, block: "l4_block_model.L4BlockModel", nonce: int = 0) -> bytes:
    """Hash an l4 block
    Args:
        hash_type: SupportedHashes enum type
        block: L4BlockModel with appropriate data to hash
        nonce: (OPTIONAL) A nonce in the form of a positive integer
    Returns:
        Bytes for the hash of the block
    """
    # Get hash object
    proof_hash = get_hash_obj(hash_type)
    # Create hash for message signing
    for curr in l4_block_hash_order:
        proof_hash.update(block.__dict__[curr].encode("utf-8"))
    for validation in block.validations:
        for curr in l4_block_validation_hash_order:
            proof_hash.update(validation[curr].encode("utf-8"))
        # For hashing purposes, treat True as a 1 byte, and treat False as a 0 byte
        if validation["valid"]:
            proof_hash.update(b"\x01")
        else:
            proof_hash.update(b"\x00")
    if nonce:
        proof_hash.update(int_to_unsigned_bytes(nonce))
    return proof_hash.digest()


def hash_l5_block(hash_type: SupportedHashes, block: "l5_block_model.L5BlockModel", nonce: int = 0) -> bytes:
    """Hash an l5 block
    Args:
        hash_type: SupportedHashes enum type
        block: L5BlockModel with appropriate data to hash
        nonce: (OPTIONAL) A nonce in the form of a positive integer
    Returns:
        Bytes for the hash of the block
    """
    # Get hash object
    proof_hash = get_hash_obj(hash_type)
    # Create hash for message signing
    for curr in l5_block_hash_order:
        proof_hash.update(block.__dict__[curr].encode("utf-8"))
    for record in block.l4_blocks:
        proof_hash.update(record.encode("utf-8"))
    # if nonce:
    #     proof_hash.update(int_to_unsigned_bytes(nonce))
    return proof_hash.digest()


def make_generic_signature(
    encryption_type: SupportedEncryption, hash_type: SupportedHashes, priv_key: Union["PrivateKey"], content_bytes: bytes
) -> str:
    """Make a generic signature for some content bytes
    Args:
        encryption_type: SupportedEncryption enum type
        hash_type: SupportedHashes enum type
        priv_key: private key object defined by encryption_type
        content_bytes: python bytes object to sign
    Returns:
        Base 64 encoded signature string
    """
    # Get the hash (signature message) first
    proof_hash = get_hash_obj(hash_type)
    proof_hash.update(content_bytes)
    sig_message = proof_hash.digest()
    # Return the signature
    return encrypt_message(encryption_type, priv_key, sig_message)


def check_generic_signature(
    encryption_type: SupportedEncryption, hash_type: SupportedHashes, pub_key: Union["PublicKey"], content_bytes: bytes, signature_bytes: bytes
) -> bool:
    """Make a generic signature for some content bytes
    Args:
        encryption_type: SupportedEncryption enum type
        hash_type: SupportedHashes enum type
        pub_key: public key object defined by encryption_type
        content_bytes: python bytes object of signed content
        signature_bytes: python bytes object of signature
    Returns:
        boolean if valid signature
    """
    # Get the hash (signature message) first
    proof_hash = get_hash_obj(hash_type)
    proof_hash.update(content_bytes)
    sig_message = proof_hash.digest()
    # Validate the actual signature
    return verify_signature(encryption_type, pub_key, sig_message, signature_bytes)


def encrypt_message(encryption_type: SupportedEncryption, priv_key: Union["PrivateKey"], message_bytes: bytes) -> str:
    """Encrypt a 32byte message (typically a hash, to use as a signature)
    Args:
        encryption_type: SupportedEncryption enum type
        priv_key: private key object defined by encryption_type
        message_bytes: 32 byte python bytes object to encrypt
    Returns:
        Base 64 encoded signature string
    Raises:
        NotImplementedError: Invalid SupportedEncryption provided
    """
    sig_bytes = None
    if encryption_type == SupportedEncryption.secp256k1:
        sig_bytes = priv_key.ecdsa_serialize(priv_key.ecdsa_signature_normalize(priv_key.ecdsa_sign(msg=message_bytes, raw=True))[1])
    else:
        raise NotImplementedError("Unsupported encryption type")
    return base64.b64encode(sig_bytes).decode("ascii")


def encrypt_secp256k1_message_compact(priv_key: Union["PrivateKey"], message_bytes: bytes) -> str:
    """Encrypt a 32byte message (typically a hash, to use as a signature) (in its compact form)
    Args:
        priv_key: private key object defined by encryption_type
        message_bytes: 32 byte python bytes object to encrypt
    Returns:
        Base 64 encoded signature string
    """
    sig_bytes = priv_key.ecdsa_serialize_compact(priv_key.ecdsa_signature_normalize(priv_key.ecdsa_sign(msg=message_bytes, raw=True))[1])
    return base64.b64encode(sig_bytes).decode("ascii")


def verify_signature(encryption_type: SupportedEncryption, pub_key: Union["PublicKey"], message_bytes: bytes, signature_bytes: bytes) -> bool:
    """Verify a signature with a given encryption type, message, and signature to use
    Args:
        encryption_type: SupportedEncryption enum type
        pub_key: public key object defined by encryption_type
        message_bytes: 32 byte python bytes object of the message to use in checking
        signature_bytes: python bytes object of the signature to check
    Returns:
        Boolean if signature is valid given inputs
    Raises:
        NotImplementedError: Invalid SupportedEncryption provided
    """
    if encryption_type == SupportedEncryption.secp256k1:
        return pub_key.ecdsa_verify(msg=message_bytes, raw=True, raw_sig=pub_key.ecdsa_deserialize(signature_bytes))
    else:
        raise NotImplementedError("Unsupported encryption type")


def pow_item(hash_type: SupportedHashes, item: Any, hash_method: Callable, complexity: int) -> Tuple[str, int]:
    """Perform a PoW operation on an item, given a hash_method to match complexity
    Args:
        hash_type: SupportedHashes enum type (passed as the first parameter into hash_method)
        item: item to do PoW with (passed as the second parameter into hash_method)
        hash_method: python function which takes hash_type, item, nonce
        complexity: number of bits of complexity required
    Returns:
        Tuple where index 0 is a Base64 encoded string of the generated hash and index 1 is the nonce
    """
    nonce = 1
    # Because python doesn't have do-while, we have to break out of a while True loop
    block_hash = None
    while True:
        block_hash = hash_method(hash_type, item, nonce)
        if check_complexity(block_hash, complexity):
            break
        nonce += 1
    return (base64.b64encode(block_hash).decode("ascii"), nonce)


def sign_transaction(
    hash_type: SupportedHashes, encryption_type: SupportedEncryption, priv_key: Union["PrivateKey"], transaction: "transaction_model.TransactionModel"
) -> Tuple[str, str]:
    """Sign a transaction
    Args:
        hash_type: SupportedHashes enum type
        encryption_type: SupportedEncryption enum type
        priv_key: private key object defined by encryption_type
        transaction: TransactionModel with appropriate data to sign
    Returns:
        Tuple of strings where index 0 is the base64 encoded full hash and index 1 is the base64 encoded stripped signature
    """
    # Optimization information:
    # Time taken per section on a t2.medium with blake2b/secp256k1
    # set up hash objects: 2.697%
    # hash data: 6.065%
    # encrypt hash: 88.249%
    # encode proof bytes: 2.988%

    # Get hashes
    full_hash_bytes = hash_full_transaction(hash_type, transaction)
    stripped_hash_bytes = hash_stripped_transaction(hash_type, full_hash_bytes, transaction)

    # Encrypt Hash (Sign)
    signature_string = encrypt_message(encryption_type, priv_key, stripped_hash_bytes)
    # Encode proof bytes
    return (base64.b64encode(full_hash_bytes).decode("ascii"), signature_string)


def verify_stripped_transaction(
    hash_type: SupportedHashes,
    encryption_type: SupportedEncryption,
    pub_key: Union["PublicKey"],
    stripped_transaction: "transaction_model.TransactionModel",
) -> bool:
    """Verify a stripped transaction
    Args:
        hash_type: SupportedHashes enum type
        encryption_type: SupportedEncryption enum type
        pub_key: public key object defined by encryption_type
        stripped_transaction: TransactionModel with appropriate data to verify
    Returns:
        Boolean if valid signed transaction
    """
    # Get hash for stripped transaction
    hash_bytes = hash_stripped_transaction(hash_type, base64.b64decode(stripped_transaction.full_hash), stripped_transaction)

    return verify_signature(encryption_type, pub_key, hash_bytes, base64.b64decode(stripped_transaction.signature))


def verify_full_transaction(
    hash_type: SupportedHashes,
    encryption_type: SupportedEncryption,
    pub_key: Union["PublicKey"],
    full_transaction: "transaction_model.TransactionModel",
) -> bool:
    """Verify a full transaction
    Args:
        hash_type: SupportedHashes enum type
        encryption_type: SupportedEncryption enum type
        pub_key: public key object defined by encryption_type
        full_transaction: TransactionModel with appropriate data to verify
    Returns:
        Boolean if valid signed and hashed transaction
    """
    # First verify the stripped transaction to check for valid signature before checking full hash
    if verify_stripped_transaction(hash_type, encryption_type, pub_key, full_transaction):
        full_hash_bytes = hash_full_transaction(hash_type, full_transaction)
        # Compare computed hash bytes to block's provided hash
        return base64.b64decode(full_transaction.full_hash) == full_hash_bytes
    else:
        return False


def check_complexity(check_bytes: bytes, complexity: int) -> bool:
    """Check the complexity of a bystream to see if it has the proper amount of leading 0 bits
    Args:
        bytes: byte stream to check for complexity bits
        complexity: number of leading bits that must be 0 in order to pass complexity
    Returns:
        Boolean true if passing complexity and false if not
    """
    # First check full bytes
    num_bytes = complexity // 8
    for i in range(num_bytes):
        if check_bytes[i] != 0:
            return False
    complex_remainder = complexity % 8
    # If complexity is a factor of 8 (full byte) no remaining bit checking is needed
    if complex_remainder == 0:
        return True
    return check_bytes[num_bytes] < 2 ** (8 - (complex_remainder))


def pow_l1_block(hash_type: SupportedHashes, block: "l1_block_model.L1BlockModel", complexity: int = 8) -> Tuple[str, int]:
    """Do proof of work on an l1 block
    Args:
        hash_type: SupportedHashes enum type
        block: L1BlockModel to do proof of work on
        complexity: Number of bits that must be 0 at the front of the PoW hash
    Returns:
        Tuple where index 0 is a Base64 encoded string of the generated hash and index 1 is the nonce
    """
    return pow_item(hash_type, block, hash_l1_block, complexity)


def sign_l1_block(
    hash_type: SupportedHashes, encryption_type: SupportedEncryption, priv_key: Union["PrivateKey"], block: "l1_block_model.L1BlockModel"
) -> str:
    """Sign a level 1 block
    Args:
        hash_type: SupportedHashes enum type
        encryption_type: SupportedEncryption enum type
        priv_key: private key object defined by encryption_type
        block: L1BlockModel with appropriate data to sign
    Returns:
        Base64 encoded string of the block signature
    """
    # Get hash for signature
    hash_bytes = hash_l1_block(hash_type, block)

    return encrypt_message(encryption_type, priv_key, hash_bytes)


def pow_l2_block(hash_type: SupportedHashes, block: "l2_block_model.L2BlockModel", complexity: int = 8) -> Tuple[str, int]:
    """Do proof of work on an l2 block
    Args:
        hash_type: SupportedHashes enum type
        block: L2BlockModel to do proof of work on
        complexity: Number of bits that must be 0 at the front of the PoW hash
    Returns:
        Tuple where index 0 is a Base64 encoded string of the generated hash and index 1 is the nonce
    """
    return pow_item(hash_type, block, hash_l2_block, complexity)


def sign_l2_block(
    hash_type: SupportedHashes, encryption_type: SupportedEncryption, priv_key: Union["PrivateKey"], block: "l2_block_model.L2BlockModel"
) -> str:
    """Sign a level 2 block
    Args:
        hash_type: SupportedHashes enum type
        encryption_type: SupportedEncryption enum type
        priv_key: private key object defined by encryption_type
        block: L2BlockModel with appropriate data to sign
    Returns:
        Base64 encoded string of the block signature
    """
    # Get hash for the block to sign
    hash_bytes = hash_l2_block(hash_type, block)

    return encrypt_message(encryption_type, priv_key, hash_bytes)


def pow_l3_block(hash_type: SupportedHashes, block: "l3_block_model.L3BlockModel", complexity: int = 8) -> Tuple[str, int]:
    """Do proof of work on an l3 block
    Args:
        hash_type: SupportedHashes enum type
        block: L3BlockModel to do proof of work on
        complexity: Number of bits that must be 0 at the front of the PoW hash
    Returns:
        Tuple where index 0 is a Base64 encoded string of the generated hash and index 1 is the nonce
    """
    return pow_item(hash_type, block, hash_l3_block, complexity)


def sign_l3_block(
    hash_type: SupportedHashes, encryption_type: SupportedEncryption, priv_key: Union["PrivateKey"], block: "l3_block_model.L3BlockModel"
) -> str:
    """Sign a level 3 block
    Args:
        hash_type: SupportedHashes enum type
        encryption_type: SupportedEncryption enum type
        priv_key: private key object defined by encryption_type
        block: L3BlockModel with appropriate data to sign
    Returns:
        Base64 encoded string of the block signature
    """
    # Get hash for the block to sign
    hash_bytes = hash_l3_block(hash_type, block)

    return encrypt_message(encryption_type, priv_key, hash_bytes)


def pow_l4_block(hash_type: SupportedHashes, block: "l4_block_model.L4BlockModel", complexity: int = 8) -> Tuple[str, int]:
    """Do proof of work on an l4 block
    Args:
        hash_type: SupportedHashes enum type
        block: L4BlockModel to do proof of work on
        complexity: Number of bits that must be 0 at the front of the PoW hash
    Returns:
        Tuple where index 0 is a Base64 encoded string of the generated hash and index 1 is the nonce
    """
    return pow_item(hash_type, block, hash_l4_block, complexity)


def sign_l4_block(
    hash_type: SupportedHashes, encryption_type: SupportedEncryption, priv_key: Union["PrivateKey"], block: "l4_block_model.L4BlockModel"
) -> str:
    """Sign a level 4 block
    Args:
        hash_type: SupportedHashes enum type
        encryption_type: SupportedEncryption enum type
        priv_key: private key object defined by encryption_type
        block: L4BlockModel with appropriate data to sign
    Returns:
        Base64 encoded string of the block signature
    """
    # Get hash for the block to sign
    hash_bytes = hash_l4_block(hash_type, block)

    return encrypt_message(encryption_type, priv_key, hash_bytes)


def sign_l5_block(
    hash_type: SupportedHashes, encryption_type: SupportedEncryption, priv_key: Union["PrivateKey"], block: "l5_block_model.L5BlockModel"
) -> str:
    """Sign a level 5 block
    Args:
        hash_type: SupportedHashes enum type
        encryption_type: SupportedEncryption enum type
        priv_key: private key object defined by encryption_type
        block: L5BlockModel with appropriate data to sign
    Returns:
        Base64 encoded string of the block signature
    """
    # Get hash for the block to sign
    hash_bytes = hash_l5_block(hash_type, block)

    return encrypt_message(encryption_type, priv_key, hash_bytes)


def verify_l1_block_trust(
    hash_type: SupportedHashes, encryption_type: SupportedEncryption, pub_key: Union["PublicKey"], block: "l1_block_model.L1BlockModel"
) -> bool:
    """Verify a level 1 block with trust scheme
    Args:
        hash_type: SupportedHashes enum type
        encryption_type: SupportedEncryption enum type
        pub_key: public key object defined by encryption_type
        block: L1BlockModel with appropriate data to verify
    Returns:
        Boolean if valid signed block
    """
    # Get hash for signature message verification
    hash_bytes = hash_l1_block(hash_type, block)

    return verify_signature(encryption_type, pub_key, hash_bytes, base64.b64decode(block.proof))


def verify_l2_block_trust(
    hash_type: SupportedHashes, encryption_type: SupportedEncryption, pub_key: Union["PublicKey"], block: "l2_block_model.L2BlockModel"
) -> bool:
    """Verify a level 2 block with trust scheme
    Args:
        hash_type: SupportedHashes enum type
        encryption_type: SupportedEncryption enum type
        pub_key: public key object defined by encryption_type
        block: L2BlockModel with appropriate data to verify
    Returns:
        Boolean if valid signed block
    """
    # Get hash for the message signature
    hash_bytes = hash_l2_block(hash_type, block)

    return verify_signature(encryption_type, pub_key, hash_bytes, base64.b64decode(block.proof))


def verify_l3_block_trust(
    hash_type: SupportedHashes, encryption_type: SupportedEncryption, pub_key: Union["PublicKey"], block: "l3_block_model.L3BlockModel"
) -> bool:
    """Verify a level 3 block with trust scheme
    Args:
        hash_type: SupportedHashes enum type
        encryption_type: SupportedEncryption enum type
        pub_key: public key object defined by encryption_type
        block: L3BlockModel with appropriate data to verify
    Returns:
        Boolean if valid signed block
    """
    # Get hash for the message signature
    hash_bytes = hash_l3_block(hash_type, block)

    return verify_signature(encryption_type, pub_key, hash_bytes, base64.b64decode(block.proof))


def verify_l4_block_trust(
    hash_type: SupportedHashes, encryption_type: SupportedEncryption, pub_key: Union["PublicKey"], block: "l4_block_model.L4BlockModel"
) -> bool:
    """Verify a level 4 block with trust scheme
    Args:
        hash_type: SupportedHashes enum type
        encryption_type: SupportedEncryption enum type
        pub_key: public key object defined by encryption_type
        block: L4BlockModel with appropriate data to verify
    Returns:
        Boolean if valid signed block
    """
    # Get hash for the message signature
    hash_bytes = hash_l4_block(hash_type, block)

    return verify_signature(encryption_type, pub_key, hash_bytes, base64.b64decode(block.proof))


def verify_l5_block_trust(
    hash_type: SupportedHashes, encryption_type: SupportedEncryption, pub_key: Union["PublicKey"], block: "l5_block_model.L5BlockModel"
) -> bool:
    """Verify a level 5 block with trust scheme
    Args:
        hash_type: SupportedHashes enum type
        encryption_type: SupportedEncryption enum type
        pub_key: public key object defined by encryption_type
        block: L5BlockModel with appropriate data to verify
    Returns:
        Boolean if valid signed block
    """
    # Get hash for the message signature
    hash_bytes = hash_l5_block(hash_type, block)

    return verify_signature(encryption_type, pub_key, hash_bytes, base64.b64decode(block.proof))


def verify_l1_block_pow(hash_type: SupportedHashes, block: "l1_block_model.L1BlockModel", complexity: int = 8) -> bool:
    """Verify a level 1 block with proof of work scheme
    Args:
        hash_type: SupportedHashes enum type
        block: L1BlockModel with appropriate data to verify
    Returns:
        Boolean if valid hashed block with appropriate nonce
    """
    # Get hash for PoW calculation to compare
    hash_bytes = hash_l1_block(hash_type, block, block.nonce)
    # Make sure it matches complexity requirements
    if not check_complexity(hash_bytes, complexity):
        return False
    # Check that the hash bytes match what the block provided
    return hash_bytes == base64.b64decode(block.proof)


def verify_l2_block_pow(hash_type: SupportedHashes, block: "l2_block_model.L2BlockModel", complexity: int = 8) -> bool:
    """Verify a level 2 block with proof of work scheme
    Args:
        hash_type: SupportedHashes enum type
        block: L2BlockModel with appropriate data to verify
    Returns:
        Boolean if valid hashed block with appropriate nonce
    """
    # Get hash for PoW calculation to compare
    hash_bytes = hash_l2_block(hash_type, block, block.nonce)
    # Make sure it matches complexity requirements
    if not check_complexity(hash_bytes, complexity):
        return False
    # Check that the hash bytes match what the block provided
    return hash_bytes == base64.b64decode(block.proof)


def verify_l3_block_pow(hash_type: SupportedHashes, block: "l3_block_model.L3BlockModel", complexity: int = 8) -> bool:
    """Verify a level 3 block with proof of work scheme
    Args:
        hash_type: SupportedHashes enum type
        block: L3BlockModel with appropriate data to verify
    Returns:
        Boolean if valid hashed block with appropriate nonce
    """
    # Get hash for PoW calculation to compare
    hash_bytes = hash_l3_block(hash_type, block, block.nonce)
    # Make sure it matches complexity requirements
    if not check_complexity(hash_bytes, complexity):
        return False
    # Check that the hash bytes match what the block provided
    return hash_bytes == base64.b64decode(block.proof)


def verify_l4_block_pow(hash_type: SupportedHashes, block: "l4_block_model.L4BlockModel", complexity: int = 8) -> bool:
    """Verify a level 4 block with proof of work scheme
    Args:
        hash_type: SupportedHashes enum type
        block: L4BlockModel with appropriate data to verify
    Returns:
        Boolean if valid hashed block with appropriate nonce
    """
    # Get hash for PoW calculation to compare
    hash_bytes = hash_l4_block(hash_type, block, block.nonce)
    # Make sure it matches complexity requirements
    if not check_complexity(hash_bytes, complexity):
        return False
    # Check that the hash bytes match what the block provided
    return hash_bytes == base64.b64decode(block.proof)

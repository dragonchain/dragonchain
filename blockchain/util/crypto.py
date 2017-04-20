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

"""
Utility library for transaction operations
"""

import time
import logging
logging.basicConfig()
import hashlib

try:
    import json
except:
    import simplejson as json

from ecdsa import SigningKey,   \
                  VerifyingKey, \
                  BadSignatureError

non_included_txn_items = {'block_id', 'status', 'creator_id'}


def sign_transaction(signatory,
                     private_key_string,
                     public_key_string,
                     transaction,
                     log=logging.getLogger(__name__)):
    """
    Sign a transaction
    :param signatory: Name or identifier of the signing party (the caller)
    :param private_key_string:
    :param public_key_string:
    :param transaction: Transaction to sign
    :param log:
    :return: Transaction with assembled signature field
    """
    hashed_items = []

    child_signature = None
    if "signature" in transaction:
        child_signature = transaction["signature"]
        log.info("Saving the child signature:  %s" % str(child_signature))
        # add old signature digest to hash list if there was one
        if 'digest' in child_signature:
            log.info("Adding signature digest to hash list")
            hashed_items.append(child_signature["digest"])

    signature_ts = int(time.time())

    log.info("Loading private key from string")
    ecdsa_signing_key = SigningKey.from_pem(private_key_string)

    # add transaction header info to hashed_items
    transaction_header = transaction["header"]
    for header_key in transaction_header:
        if header_key not in non_included_txn_items:
            hashed_items.append(transaction_header[header_key])

    # append my signing info for hashing
    hashed_items.append(signatory)
    hashed_items.append(signature_ts)
    hashed_items.append(public_key_string)

    log.info("Creating stripped hash")
    stripped_hash = final_hash(hashed_items)
    log.debug("stripped_transaction_hash=%s" % stripped_hash)

    # put hashed transaction payload back and append to hashed_items
    if transaction["payload"]:
        log.info("Hashing payload")
        hashed_items.append(deep_hash(transaction["payload"]))
        # generate hash with with hashed payload included
        log.info("Generating hash")
        hash = final_hash(hashed_items)
    else:
        hash = stripped_hash

    # merge stripped_hash and hash to send for signing
    log.info("Merging stripped and full hash")
    merged_hash = merge_hashes(stripped_hash, hash)

    # sign merged hash
    log.info("Signing merged hash")
    signature = ecdsa_signing_key.sign(str(merged_hash))
    log.info("Base64 encoding the signature")
    digest = signature.encode('base64')

    assemble_sig_block(transaction, signatory, public_key_string, digest, hash, signature_ts, stripped_hash,
                       child_signature)

    return transaction


def sign_verification_record(signatory,
                             prior_block_hash,
                             lower_hash,
                             public_key_string,
                             private_key_string,
                             block_id,
                             phase,
                             origin_id,
                             verification_ts,
                             public_transmission,
                             verification_info):
    """
    Sign a (block) verification record
    :param signatory: Name or identifier of the signing party (the caller)
    :param prior_block_hash: Hash of the prior block (verification record with the same origin_id, phase, and signatory)
    :param lower_hash: Hash of the lower phase verification record
    :param public_key_string: hashed and inserted into signature block for later validation
    :param private_key_string: private key used for generating signature
    :param block_id: Verification record block ID
    :param phase: Verification record phase
    :param origin_id: ID of the origin node (phase 1 node)
    :param verification_ts:
    :param public_transmission:
    :param verification_info: Phase specific information to be included in the signature
        - phase_1: list of approved transactions (dictionaries)
        - phase_2: valid_tx ID list, invalid_tx ID list, business ID, deploy_location
        - phase_3: phase_2 count, business_diversity list, deploy_loc_diversity list
        - phase_4: Nothing (notary function only)
        - phase_5: One of:
            - transaction
            - verification_record
            - hash
            - arbitrary string
    :return: verification record with assembled signature field
    """

    ecdsa_signing_key = SigningKey.from_pem(private_key_string)
    block_info = {}
    signature_ts = int(time.time())
    hashed_items = []

    # append prior_block_hash and lower_hash
    hashed_items.append(prior_block_hash)
    hashed_items.append(lower_hash)

    # append my signing info for hashing
    hashed_items.append(signatory)
    hashed_items.append(signature_ts)
    hashed_items.append(public_key_string)

    # append given info for hashing
    hashed_items.append(block_id)
    hashed_items.append(phase)
    hashed_items.append(origin_id)
    hashed_items.append(verification_ts)

    # append verification_info hash for hashing
    hashed_items.append(deep_hash(verification_info))

    verification_hash = final_hash(hashed_items)

    signature = ecdsa_signing_key.sign(verification_hash)
    digest = signature.encode('base64')

    verification_record = {
        "verification_ts": int(time.time()),
        "block_id": block_id,
        "origin_id": origin_id,
        "phase": int(phase),
        "prior_hash": prior_block_hash,
        "lower_hash": lower_hash,
        "public_transmission": public_transmission,
        "verification_info": verification_info  # special phase info
    }

    assemble_sig_block(verification_record, signatory, public_key_string, digest, verification_hash, signature_ts)

    block_info['block_id'] = block_id
    block_info['phase'] = int(phase)
    block_info['verification_record'] = verification_record

    return block_info


def sign_subscription(signatory, subscription, private_key_string, public_key_string):
    """
    sign a subscription (deep hash of criteria, signatory, signature timestamp, public key)
    param signatory: Name or identifier of the signing party (the caller)
    param subscription: all fields of subscription signed
    param private_key_string: private key used for generating signature
    param public_key_string: hashed and inserted into signature block for later validation
    """
    ecdsa_signing_key = SigningKey.from_pem(private_key_string)
    signature_ts = int(time.time())
    hashed_items = []

    # append criteria for hashing
    hashed_items.append(deep_hash(subscription['criteria']))

    # append sub create timestamp for hashing
    hashed_items.append(subscription['create_ts'])

    hashed_items.append(signatory)
    hashed_items.append(signature_ts)
    hashed_items.append(public_key_string)

    verification_hash = final_hash(hashed_items)

    signature = ecdsa_signing_key.sign(verification_hash)
    digest = signature.encode('base64')

    signature_block = assemble_sig_block(subscription, signatory, public_key_string, digest, verification_hash, signature_ts)

    return signature_block


def valid_transaction_sig(transaction, test_mode=False, log=logging.getLogger(__name__)):
    """
    Validate the signature on a passed transaction.
    Checks signature validity and that the signature's hash is equal to a newly calculated hash.
    If no signature is present, will return True (signature is _not_ required for a transaction).
    :param transaction: Transaction
    :param test_mode: errors not logged in test mode
    :param log: message logger
    :return: True on valid or non-existent transaction signature, False otherwise.
    """

    """ returns true on valid transaction signature, false otherwise """
    hashed_items = []

    if "signature" in transaction:
        try:
            signature_block = transaction["signature"]
            while signature_block:

                log.debug("this_signature:  %s" % str(signature_block))

                validate_signature(signature_block, log)

                log.info("Hash validation...")

                # add transaction header info for hash verification
                transaction_header = transaction["header"]
                for header_key in transaction_header:
                    # TODO: create a global req_header_info list to check what to add in signing and what to check for here
                    if header_key not in non_included_txn_items:
                        hashed_items.append(transaction_header[header_key])

                # checking if this signature has a child signature digest and adding to hash verification
                if "child_signature" in signature_block and signature_block["child_signature"]:
                    hashed_items.append(signature_block["child_signature"]["signature"])

                # adding signature info for hash verification
                hashed_items.append(signature_block["signatory"])
                hashed_items.append(signature_block["signature_ts"])
                hashed_items.append(signature_block["public_key"])

                log.info("Performing stripped hash verification")
                stripped_hash = final_hash(hashed_items)
                if not stripped_hash == signature_block["stripped_hash"]:
                    return False

                if transaction["payload"]:
                    log.info("Performing full hash verification")
                    hashed_items.append(deep_hash(transaction["payload"]))
                    full_hash = final_hash(hashed_items)

                    if not full_hash == signature_block["hash"]:
                        return False

                if "child_signature" in signature_block:
                    log.info("Reviewing the child signature")
                    signature_block = signature_block["child_signature"]
                else:
                    signature_block = None

        except BadSignatureError:
            if not test_mode:
                log.error("BadSignatureError detected.")
            return False
        except:
            if not test_mode:
                log.warning("An unexpected error has occurred. Possible causes: KeyError")
            raise  # re-raise the exception

    return True


def validate_signature(signature_block, log=logging.getLogger(__name__)):
    """
    Validates signature of verification record or transaction accounting for presence of
        "stripped_hash" in transaction signatures
    :param signature_block: dict of signature
    :param log: message logger
    :return: True on valid signature, False otherwise.
    """

    """ validate signature using provided stripped and full hashes """

    verifying_key = VerifyingKey.from_pem(signature_block["public_key"])

    log.info("Decoding the digest")
    decoded_digest = signature_block["signature"].decode('base64')

    log.info('Performing signature verification')
    # checking stripped hash if this is a transaction signature
    if "stripped_hash" in signature_block and signature_block['stripped_hash']:
        merged_hash = merge_hashes(signature_block["stripped_hash"], signature_block["hash"])
        verifying_key.verify(decoded_digest, str(merged_hash))
    else:
        verifying_key.verify(decoded_digest, str(signature_block["hash"]))
    # signature hash is valid
    return True


def validate_verification_record(record, verification_info, test_mode=False, log=logging.getLogger(__name__)):
    """
    Validate signature in a verification record.
    Checks signature validity and that the signature's hash is equal to a newly calculated hash.
    :param record: General/common verification record fields
    :param verification_info: Special, phase specific verification record fields/data
    :param test_mode: flag set in testing to avoid unwanted error messages
    :param log:
    :return: True if signature is valid and hash is equal to a newly calculated hash, False otherwise.
    """
    hashed_items = []
    try:
        signature_block = record['signature']

        validate_signature(signature_block)

        hashed_items.append(record['prior_hash'])
        hashed_items.append(record['lower_hash'])

        hashed_items.append(signature_block['signatory'])
        hashed_items.append(signature_block['signature_ts'])
        hashed_items.append(signature_block['public_key'])

        # append given info for hashing
        hashed_items.append(record['block_id'])
        hashed_items.append(record['phase'])
        hashed_items.append(record['origin_id'])
        hashed_items.append(record['verification_ts'])

        # append arbitrary verification info for hashing
        hashed_items.append(deep_hash(verification_info))

        verification_hash = final_hash(hashed_items)
        if not verification_hash == signature_block['hash']:
            return False

    except BadSignatureError:
        if not test_mode:
            log.error("BadSignatureError detected.")
        return False
    except:
        if not test_mode:
            log.warning("An unexpected error has occurred. Possible causes: KeyError")
        raise  # re-raise the exception

    return True


def validate_subscription(signature_block,
                          criteria,
                          create_ts,
                          subscriber_public_key,
                          log=logging.getLogger(__name__)):
    """
    validate signature in a subscription.
    checks signature validity and that the signature's hash is equal to a newly calculated hash.
    param signature_block: dict of signature
    param criteria: dict of criteria data hashed
    param create_ts: time subscription was created
    param subscriber_public_key: public key hashed
    """
    hashed_items = []
    try:
        validate_signature(signature_block)

        hashed_items.append(deep_hash(criteria))

        hashed_items.append(create_ts)

        hashed_items.append(signature_block['signatory'])
        hashed_items.append(signature_block['signature_ts'])
        hashed_items.append(subscriber_public_key)

        verification_hash = final_hash(hashed_items)
        if not verification_hash == signature_block['hash']:
            return False

    except BadSignatureError:
        log.error("BadSignatureError detected.")
        return False
    except:
        log.warning("An unexpected error has occurred. Possible causes: KeyError")
        raise  # re-raise the exception

    return True


def assemble_sig_block(record, signatory, public_key_string, signature, hash, signature_ts, stripped_hash=None,
                       child_signature=None, log=logging.getLogger(__name__)):
    """
    :param record: Record to which a standard signature will be added (TODO consider to move this to calling functions)
    :param signatory: Name or identifier of the signing party (the caller)
    :param public_key_string: Encoded public key of the signing keypair
    :param signature: The digital signature
    :param hash: Hash of information which was signed
    :param signature_ts: Timestamp of the signing action (included in the signature)
    :param stripped_hash: Optional hash (used for transaction with payload "stripped").
    :param child_signature: Optional nested signature
    :param log:
    :return: The record with signature field added.
    """
    signature_block = {
        "signatory": signatory,
        "signature": signature,
        "hash": hash,
        "public_key": public_key_string,
        "signature_ts": signature_ts
    }

    if not record:
        return signature_block

    # setting signature name
    record["signature"] = signature_block

    # setting stripped and full hashes
    if stripped_hash:
        record["signature"]["stripped_hash"] = stripped_hash

    # set the child signature if there was one
    if child_signature:
        record["signature"]["child_signature"] = child_signature


def bytes2long(str):
    """
    Utility function to convert string to hexidecimal representation and cast to long for deterministic hashing.
    TODO argument validation
    :param str: String to convert
    :return: integer representation of passed string
    """
    return long(str.encode('hex'), 16)


def deterministic_hash(items):
    """
    Intermediary hashing function that allows deterministic hashing of a list of items.
    :param items: List of items to hash
    :return: Numeric, deterministic hash, returns 0 if item is none
    """
    h = 0
    for item in items:
        if not item:
            pass
        elif not isinstance(item, (int, long)):
            h ^= bytes2long(item)
        else:
            h ^= item
    return h


def deep_hash(thing):
    """
    Intermediary hashing function that allows creation of a hash from a dictionary, list, tuple, or set to any level,
        that contains only other hashable types (including any lists, tuples, sets, and dictionaries).
    :param thing: Arbitrary dict, list, tuple, or set to hash
    :return: Numeric, deterministic hash
    """
    if not thing:
        return 0
    elif isinstance(thing, (set, tuple, list)):
        return deterministic_hash([deep_hash(e) for e in thing])
    elif not isinstance(thing, dict):
        return hash(thing)

    list_to_hash = []
    for k, v in thing.items():
        list_to_hash.append(k)
        list_to_hash.append(deep_hash(v))

    return deterministic_hash(list_to_hash)


def final_hash(items, type=512):
    """
    Deterministic hashing function that should be used for any full hashing in the system.
    :param items: A list of items to hash deterministically.
    :return: finalized deterministic sha512 hash
    """
    if type == 256:
        """ returns final sha256 hash """
        hash_object = hashlib.sha256(str(deterministic_hash(items)))
    else:
        """ returns final sha512 hash """
        hash_object = hashlib.sha512(str(deterministic_hash(items)))
    hex_dig = hash_object.hexdigest()

    return hex_dig


def merge_hashes(stripped_hash, hash):
    """
    For transaction hashing, merge stripped_hash (excluding payload) and hash (including payload) for processing.
    :param stripped_hash: Hash of the stripped transaction (no payload).
    :param hash: Hash of the complete transaction.
    :return: Deterministic unified hash
    """
    hashed_items = [stripped_hash, hash]
    return deterministic_hash(hashed_items)

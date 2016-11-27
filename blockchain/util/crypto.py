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
import hashlib

from blockchain.util.thrift_conversions import thrift_record_to_dict

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
    sign verification record (common and special info among each phase)
    * signatory (current node's name/id)
    * prior_block_hash
    * lower_hash
    * public_key
    * private_key
    * block_id
    * phase
    * origin_id (original phase_1 node_id)
    * verification_ts
    * verification_info (special info per phase)
        - phase_1 (approved transactions)
        - phase_2 (valid_txs, invalid_txs, business, deploy_location, verification_sig)
        - phase_3 (phase_2 count, business_diversity list, deploy_loc_diversity list, verification_sig)
        - phase_4
        - phase_5
    """
    # signature, transaction_hash = \
    #     sign_signatures(map(lambda tx: tx["signature"], approved_transactions), private_key_string)

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


def valid_transaction_sig(transaction, log=logging.getLogger(__name__)):
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
            return False
        except:
            log.warning("An unexpected error has occurred")
            raise  # re-raise the exception

    return True


def validate_signature(signature_block, log=logging.getLogger(__name__)):
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


def validate_verification_record(record, verification_info, log=logging.getLogger(__name__)):
    """
    validate verification record signature
    * verification_record - general info per phase - signing name, timestamp, pub_key, block_id, etc.
    * verification_info - arbitrary data per phase such as approved transactions
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
        return False
    except:
        log.warning("An unexpected error has occurred")
        raise  # re-raise the exception

    return True


def assemble_sig_block(record, signatory, public_key_string, signature, hash, signature_ts, stripped_hash=None,
                       child_signature=None, log=logging.getLogger(__name__)):
    """
    assemble new signature record
    optional stripped_hash and child_sig
    :param signature_ts:
    """
    # setting signature name

    record["signature"] = {
        "signatory": signatory,
        "signature": signature,
        "hash": hash,
        "public_key": public_key_string,
        "signature_ts": signature_ts
    }

    # setting stripped and full hashes
    if stripped_hash:
        record["signature"]["stripped_hash"] = stripped_hash

    # set the child signature if there was one
    if child_signature:
        record["signature"]["child_signature"] = child_signature


def bytes2long(str):
    """ converts string bytes to long; only accepts string type """
    return long(str.encode('hex'), 16)


def deterministic_hash(items):
    """ hash list of items; converts strings to longs when needed, returns 0 if item is none """
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
    Makes a hash from a dictionary, list, tuple or set to any level, that contains
    only other hashable types (including any lists, tuples, sets, and
    dictionaries).
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


def final_hash(items):
    """ returns final sha512 hash """
    hash_object = hashlib.sha512(str(deterministic_hash(items)))
    hex_dig = hash_object.hexdigest()

    return hex_dig


def merge_hashes(stripped_hash, hash):
    """ merge stripped_hash (excluding payload) and hash (including payload) """
    hashed_items = [stripped_hash, hash]
    return deterministic_hash(hashed_items)

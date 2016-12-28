#!/usr/bin/python

"""
Utility library for transaction operations
"""

from hashlib import sha256
import time
import sys
import logging

try:
    import json
except:
    import simplejson as json

from ecdsa import SigningKey,   \
                  VerifyingKey, \
                  BadSignatureError

# TODO:  Move this to a template or to an external resource
reqd = {
    "header": [
        "create_ts",
        "owner",
        "transaction_type"
    ]
}

# TODO:  Move this to a util lib
def validate_json(doc, expected = reqd):
    log = logging.getLogger(__name__)
    is_collection = lambda c: (isinstance(c, dict) or isinstance(c, list))
    for k in expected:
        try:
            log.debug(str(k) + " >> " + str(doc.keys()))
            if is_collection(k):
                validate_json(doc, k)
            elif k not in doc.keys():
                raise "Required field %s was not found in %s" % (k, str(doc))
            elif isinstance(expected, dict) and is_collection(expected[k]):
                validate_json(doc[k], expected[k])
        except:
            log.error(str(k) + " // " + str(sys.exc_info()[1]))

def bytes2long(str):
 return long(str.encode('hex'), 16)

def hash_list(items):
    hash = 0
    for item in items:
        hash ^= bytes2long(item)
    return hash

def sign_signatures(signatures,
                    private_key_string,
                    log=logging.getLogger(__name__)):
    """
    Signs a set of transactions and returns a tuple of the signature and transaction hash.
    """

    # TODO:  Add a link to the docs on this here.
    log.info("Loading private key from string")
    log.debug("priv:  %s" % private_key_string)
    ecdsa_signing_key = SigningKey.from_pem(private_key_string)

    log.info("Hashing transaction set")
    signing_hash = 0
    for item in signatures:
        signing_hash ^= bytes2long(item["digest"])

    signing_hash = str(signing_hash).encode('base64')

    log.info("Signing the transaction set string hash")
    log.debug("transaction_hash=%s"%signing_hash)
    signature = ecdsa_signing_key.sign(signing_hash)

    log.info("Base64 encoding the signature")
    signature = signature.encode('base64')

    return signature, signing_hash

def sign_transaction(signatory,
                     private_key_string,
                     public_key_string,
                     transaction,
                     log = logging.getLogger(__name__)):

    # TODO:  Add a link to the docs on this here.
    log.info("Loading private key from string")
    log.debug("priv:  %s" % private_key_string)
    ecdsa_signing_key = SigningKey.from_pem(private_key_string)

    log.info("Dumping transaction json to a string")
    transaction_str = json.dumps(transaction)

    log.info("Hashing transaction json string")
    transaction_hash = sha256(transaction_str).hexdigest()

    log.info("Signing the transaction json string hash")
    log.debug("transaction_hash=%s"% transaction_hash)
    signature = ecdsa_signing_key.sign(transaction_hash)

    log.info("Base64 encoding the signature")
    signature = signature.encode('base64')

    # keep the original child signature copy
    # while creating a new one
    child_signature = None
    if "signature" in transaction:
        child_signature = transaction["signature"]
        log.info("Saving the child signature:  %s" % str(child_signature))
    log.debug("Done dealing with the child sig")

    # current signature
    log.info("Setting the current transaction signature")
    transaction["signature"] = {}

    log.debug("Setting signatory")
    transaction["signature"]["name"] = signatory

    log.debug("Setting transaction_hash")
    transaction["signature"]["transaction_hash"] = transaction_hash

    log.debug("Setting digest")
    transaction["signature"]["digest"] = signature

    log.debug("Setting public key")
    transaction["signature"]["public_key"] = public_key_string

    log.debug("Setting sig ts")
    transaction["signature"]["signature_ts"] = int(time.time())

    # set the child signature if there was one
    if child_signature:
        transaction["signature"]["signature"] = child_signature

    return transaction

def validate_transaction(transaction, log = logging.getLogger(__name__)):
    # returns tuple: ( string|None name_of_failed_signatory, bool failed )
    # raises exceptions, but handles BadSignatureError exceptions
    try:
        this_signature = transaction["signature"]
        while this_signature:

            log.debug("this_signature:  %s" % str(this_signature))

            log.info("Creating the verifying key")
            ecdsa_verifying_key = VerifyingKey.from_pem(this_signature["public_key"])

            log.info("Decoding the digest")
            decoded_digest = this_signature["digest"].decode('base64')

            log.info('Performing the verification')
            ecdsa_verifying_key.verify(decoded_digest, this_signature["transaction_hash"])

            if "signature" in this_signature:
                log.info("Reviewing the child signature")
                this_signature = this_signature["signature"]
            else:
                this_signature = None
                break

    except BadSignatureError:
        return (this_signature["name"], False)
    except:
        # TODO:  log that something unexpected happened here.
        raise # re-raise the exception

    return (None, True)

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

""" Module for converting thrift structs to dictionaries and vice versa """

import blockchain.gen.messaging.ttypes as message_types

# **** functions below used for converting thrift types to some other structure **** #
def thrift_record_to_dict(thrift_record):
    """ returns a dictionary representation of a thrift verification_record """
    return {
        'block_id': thrift_record.block_id,
        'origin_id': thrift_record.origin_id,
        'phase': thrift_record.phase,
        'verification_ts': thrift_record.verification_ts,
        'signature': convert_thrift_signature(thrift_record.signature),
        'prior_hash': thrift_record.prior_hash,
        'lower_hash': thrift_record.lower_hash,
        'public_transmission': thrift_record.public_transmission
    }


def thrift_transaction_to_dict(thrift_transaction):
    """ returns a dictionary representation of a thrift transaction """
    payload = thrift_transaction.tx_payload
    return {
        "header": convert_thrift_header(thrift_transaction.tx_header),
        "payload": payload,
        "signature": convert_thrift_signature(thrift_transaction.tx_signature)
    }


def convert_thrift_header(thrift_header):
    """ returns a dictionary representation of a thrift transaction header """
    return {
        "actor": thrift_header.actor,
        "block_id": thrift_header.block_id,
        "business_unit": thrift_header.business_unit,
        "create_ts": thrift_header.create_ts,
        "creator_id": thrift_header.creator_id,
        "entity": thrift_header.entity,
        "family_of_business": thrift_header.family_of_business,
        "line_of_business": thrift_header.line_of_business,
        "owner": thrift_header.owner,
        "status": thrift_header.status,
        "transaction_id": thrift_header.transaction_id,
        "transaction_ts": thrift_header.transaction_ts,
        "transaction_type": thrift_header.transaction_type
    }


def convert_thrift_signature(thrift_signature):
    """ returns a dictionary representation of a thrift transaction signature """
    return {
        "signature": thrift_signature.signature,
        "hash": thrift_signature.hash,
        "signatory": thrift_signature.signatory,
        "public_key": thrift_signature.public_key,
        "signature_ts": thrift_signature.signature_ts,
        "stripped_hash": thrift_signature.strip_hash
    }


# **** functions below used for converting to thrift types **** #
def convert_to_thrift_transaction(transaction):
    """ returns a thrift representation of a transactions converted from a dictionary """
    thrift_transaction = message_types.Transaction()
    thrift_transaction.tx_header = convert_to_thrift_header(transaction['header'])
    thrift_transaction.tx_signature = convert_to_thrift_signature(transaction['signature'])

    return thrift_transaction


def convert_to_thrift_header(tx_header):
    """ returns a thrift representation of a dictionary transaction header """
    thrift_header = message_types.Header()
    thrift_header.actor = tx_header['actor']
    thrift_header.block_id = tx_header['block_id']
    thrift_header.business_unit = tx_header['business_unit']
    thrift_header.create_ts = tx_header['create_ts']
    thrift_header.creator_id = tx_header['creator_id']
    thrift_header.entity = tx_header['entity']
    thrift_header.family_of_business = tx_header['family_of_business']
    thrift_header.line_of_business = tx_header['line_of_business']
    thrift_header.owner = tx_header['owner']
    thrift_header.status = tx_header['status']
    thrift_header.transaction_id = tx_header['transaction_id']
    thrift_header.transaction_ts = tx_header['transaction_ts']
    thrift_header.transaction_type = tx_header['transaction_type']

    return thrift_header


def convert_to_thrift_signature(tx_signature):
    """ returns a thrift representation of a dictionary transaction signature """
    thrift_signature = message_types.Signature()
    if "signatory" in tx_signature:
        thrift_signature.signatory = str(tx_signature['signatory'])

    if "signature_ts" in tx_signature:
        thrift_signature.signature_ts = tx_signature['signature_ts']

    if "stripped_hash" in tx_signature:
        thrift_signature.strip_hash = tx_signature['stripped_hash']

    thrift_signature.hash = tx_signature['hash']
    thrift_signature.signature = tx_signature['signature']
    thrift_signature.public_key = tx_signature['public_key']

    return thrift_signature


def convert_to_thrift_record(record):
    """ returns a thrift representation of a dictionary VerificationRecordCommonInfo """
    thrift_record = message_types.VerificationRecordCommonInfo()
    thrift_record.block_id = record['block_id']
    thrift_record.origin_id = record['origin_id']
    thrift_record.phase = record['phase']
    thrift_record.verification_ts = record['verification_ts']
    thrift_record.lower_hash = record['lower_hash']
    thrift_record.public_transmission = record['public_transmission']

    if record['prior_hash']:
        thrift_record.prior_hash = record['prior_hash']

    thrift_record.signature = convert_to_thrift_signature(record['signature'])

    return thrift_record

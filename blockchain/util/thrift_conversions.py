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

RECORD = 'record'
VERIFICATION_RECORD = 'verification_record'
VERIFICATION_INFO = 'verification_info'


# **** functions below used for converting thrift types to some other structure **** #
def thrift_record_to_dict(thrift_record):
    """ returns a dictionary representation of a thrift verification_record """
    return {
        'block_id': thrift_record.block_id,
        'origin_id': thrift_record.origin_id,
        'phase': thrift_record.phase,
        'verification_ts': thrift_record.verification_ts,
        'verification_id': None,
        'signature': convert_thrift_signature(thrift_record.signature),
        'prior_hash': thrift_record.prior_hash,
        'lower_hash': thrift_record.lower_hash,
        'public_transmission': thrift_record.public_transmission
    }


def convert_thrift_transaction(thrift_transaction):
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


def convert_to_thrift_signature(signature):
    """ returns a thrift representation of a dictionary signature """
    thrift_signature = message_types.Signature()
    if "signatory" in signature:
        thrift_signature.signatory = str(signature['signatory'])

    if "signature_ts" in signature:
        thrift_signature.signature_ts = signature['signature_ts']

    if "stripped_hash" in signature:
        thrift_signature.strip_hash = signature['stripped_hash']

    thrift_signature.hash = signature['hash']
    thrift_signature.signature = signature['signature']
    thrift_signature.public_key = signature['public_key']

    return thrift_signature


def convert_to_thrift_record(record):
    """ returns a thrift representation of a dictionary VerificationRecordCommonInfo """
    verification_id = None
    if 'verification_id' in record:
        verification_id = record['verification_id']
    thrift_record = message_types.VerificationRecordCommonInfo()
    thrift_record.block_id = record['block_id']
    thrift_record.origin_id = record['origin_id']
    thrift_record.phase = record['phase']
    thrift_record.verification_ts = record['verification_ts']
    thrift_record.verification_id = verification_id
    thrift_record.lower_hash = record['lower_hash']
    thrift_record.public_transmission = record['public_transmission']

    if record['prior_hash']:
        thrift_record.prior_hash = record['prior_hash']

    thrift_record.signature = convert_to_thrift_signature(record['signature'])

    return thrift_record


def get_phase_1_info(phase_1):
    """ return dictionary representation of thrift phase 1 """
    return {
        RECORD: thrift_record_to_dict(phase_1.record),
        VERIFICATION_INFO: map(convert_thrift_transaction, phase_1.transactions)
    }


def get_phase_2_info(phase_2):
    """ return dictionary representation of thrift phase 2 """
    return {
        RECORD: thrift_record_to_dict(phase_2.record),
        VERIFICATION_INFO: {
            'valid_txs': map(convert_thrift_transaction, phase_2.valid_txs),
            'invalid_txs': map(convert_thrift_transaction, phase_2.invalid_txs),
            'business': phase_2.business,
            'deploy_location': phase_2.deploy_location
        }
    }


def get_phase_3_info(phase_3):
    """ return dictionary representation of thrift phase 3 """
    return {
        RECORD: thrift_record_to_dict(phase_3.record),
        VERIFICATION_INFO: {
            'lower_hashes': phase_3.lower_hashes,
            'p2_count': phase_3.p2_count,
            'businesses': phase_3.businesses,
            'deploy_locations': phase_3.deploy_locations
        }
    }


def get_phase_4_info(phase_4):
    """ return dictionary representation of thrift phase 4 """
    return {
        RECORD: thrift_record_to_dict(phase_4.record),
        VERIFICATION_INFO: phase_4.lower_hash
    }


def get_p1_message(block_info):
    """ returns thrift phase 1 message structure """
    verification_record = block_info['verification_record']
    transactions = map(convert_to_thrift_transaction, verification_record['verification_info'])
    verification_record = convert_to_thrift_record(verification_record)

    phase_1_msg = message_types.Phase_1_msg()
    phase_1_msg.record = verification_record
    phase_1_msg.transactions = transactions

    return phase_1_msg


def get_p2_message(block_info):
    """returns thrift phase 2 message structure """
    verification_record = block_info['verification_record']
    verification_info = verification_record['verification_info']

    phase_2_msg = message_types.Phase_2_msg()
    phase_2_msg.record = convert_to_thrift_record(verification_record)
    phase_2_msg.valid_txs = map(convert_to_thrift_transaction, verification_info['valid_txs'])
    phase_2_msg.invalid_txs = map(convert_to_thrift_transaction, verification_info['invalid_txs'])
    phase_2_msg.business = verification_info['business']
    phase_2_msg.deploy_location = verification_info['deploy_location']

    return phase_2_msg


def get_p3_message(block_info):
    """returns thrift phase 3 message structure """
    verification_record = block_info['verification_record']
    verification_info = verification_record['verification_info']

    phase_3_msg = message_types.Phase_3_msg()
    phase_3_msg.record = convert_to_thrift_record(verification_record)
    phase_3_msg.p2_count = verification_info['p2_count']
    phase_3_msg.businesses = verification_info['businesses']
    phase_3_msg.deploy_locations = verification_info['deploy_locations']
    phase_3_msg.lower_hashes = verification_info['lower_hashes']

    return phase_3_msg


def get_p4_message(block_info):
    """returns thrift phase 4 message structure """
    verification_record = block_info['verification_record']

    phase_4_msg = message_types.Phase_4_msg()
    phase_4_msg.record = convert_to_thrift_record(verification_record)
    phase_4_msg.lower_hash = block_info['verification_record']['lower_hash']

    return phase_4_msg


def get_verification_type(verification):
    """ construct a thrift friendly verification record for broadcast receipt """
    record = {'block_id': verification['block_id'],
              'origin_id': verification['origin_id'],
              'phase': verification['phase'],
              'verification_ts': verification['verification_ts'],
              'verification_id': verification['verification_id'],
              'lower_hash': None,
              'prior_hash': None,
              'public_transmission': None,
              'signature': verification['signature'],
              'verification_info': verification['verification_info']
              }
    info = {'verification_record': record}
    phase = verification['phase']
    verification_record = message_types.VerificationRecord()

    if phase == 1:
        verification_record.p1 = get_p1_message(info)
    elif phase == 2:
        verification_record.p2 = get_p2_message(info)
    elif phase == 3:
        verification_record.p3 = get_p3_message(info)
    elif phase == 4:
        verification_record.p4 = get_p4_message(info)

    return verification_record


def convert_thrift_verification(verification):
    """ convert thrift verification record to dict """
    record = None
    verification_info = None
    if verification.p1:
        record = verification.p1.record
        verification_info = map(convert_thrift_transaction, verification.p1.transactions)
    elif verification.p2:
        record = verification.p2.record
        verification_info = {'valid_txs': map(convert_thrift_transaction, verification.p2.valid_txs),
                             'invalid_txs': map(convert_thrift_transaction, verification.p2.invalid_txs),
                             'business': verification.p2.business,
                             'deploy_location': verification.p2.deploy_location
                             }
    elif verification.p3:
        record = verification.p3.record
        verification_info = {'lower_hashes': verification.p3.lower_hashes,
                             'p2_count': verification.p3.p2_count,
                             'businesses': verification.p3.businesses,
                             'deploy_locations': verification.p3.deploy_locations
                             }
    elif verification.p4:
        record = verification.p4.record

    verification_record = {'block_id': record.block_id,
                           'origin_id': record.origin_id,
                           'phase': record.phase,
                           'verification_ts': record.verification_ts,
                           'verification_id': record.verification_id,
                           'lower_hash': None,
                           'prior_hash': None,
                           'public_transmission': None,
                           'signature': convert_thrift_signature(record.signature),
                           'verification_info': verification_info
                           }

    return verification_record

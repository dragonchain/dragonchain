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

__author__ = "Joe Roets, Brandon Kite, Dylan Yelton, Michael Bachtel, Alex Benedetto"
__copyright__ = "Copyright 2016, Disney Connected and Advanced Technologies"
__license__ = "Apache"
__version__ = "2.0"
__maintainer__ = "Joe Roets"
__email__ = "joe@dragonchain.org"

import psycopg2
import psycopg2.extras
import uuid

from blockchain.qry import format_block_verification as format_verification_record

from postgres import get_connection_pool

""" CONSTANTS """
DEFAULT_PAGE_SIZE = 1000
GET_UNSENT_VERIFIED_RECORDS = """SELECT * FROM vr_transfers WHERE transfer_to = %s AND sent = FALSE"""
SQL_MARK_RECORD = """UPDATE vr_transfers SET sent = TRUE WHERE transfer_to = %s AND verification_id = %s"""
SQL_INSERT_QUERY = """INSERT INTO vr_transfers (
                                  origin_id,
                                  transfer_to,
                                  verification_id
                                ) VALUES (%s, %s, %s)"""


def get_unsent_verification_records(node_transmit_id):
    """ retrieve validated records that have not already been sent back to node with node_transmit_id or verification_id """

    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(get_cursor_name(), cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(GET_UNSENT_VERIFIED_RECORDS, (node_transmit_id, ))
        'An iterator that uses fetchmany to keep memory usage down'
        while True:
            results = cur.fetchmany(DEFAULT_PAGE_SIZE)
            if not results:
                break
            for result in results:
                yield format_verification_record(result)
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def insert_transfer(origin_id, transfer_to, verification_id):
    values = (
        origin_id,
        transfer_to,
        verification_id
    )
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor()
        cur.execute(SQL_INSERT_QUERY, values)
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def set_verification_sent(transfer_to, ver_id):
    """ set verifications sent field to true with matching given 'transfer_to' and 'verification_id' """

    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_MARK_RECORD, (transfer_to, ver_id))
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def get_cursor_name():
    return str(uuid.uuid4())

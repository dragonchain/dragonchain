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

from blockchain.qry import format_sub_response

from postgres import get_connection_pool

""" CONSTANTS """
DEFAULT_PAGE_SIZE = 1000
SQL_GET_ALL = """SELECT * FROM sub_vr_transfers WHERE transfer_to = %s"""
SQL_INSERT_QUERY = """INSERT INTO sub_vr_transfers (
                                  transfer_to,
                                  transactions,
                                  verifications
                                ) VALUES (%s, %s::json[], %s::json[])"""


def insert_transfer(transfer_to, transactions, verifications):
    """
    inserts new transfer record containing list of transactions and verifications
    param transfer_to: node_id to send transfer records to
    param transactions: list of json formatted transactions
    param verifications: list of json formatted verification records
    """
    values = (
        transfer_to,
        map(psycopg2.extras.Json, transactions),
        map(psycopg2.extras.Json, verifications)
    )
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor()
        cur.execute(SQL_INSERT_QUERY, values)
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def get_all(transfer_to):
    """ query for all transfer records with transfer_to matching given transfer_to id """
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(get_cursor_name(), cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_GET_ALL, (transfer_to, ))
        'An iterator that uses fetchmany to keep memory usage down'
        while True:
            results = cur.fetchmany(DEFAULT_PAGE_SIZE)
            if not results:
                break
            for result in results:
                yield format_sub_response(result)
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def get_cursor_name():
    return str(uuid.uuid4())

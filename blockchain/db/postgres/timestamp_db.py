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

import psycopg2
import psycopg2.extras
from psycopg2.extras import Json
import uuid
import time

from blockchain.qry import format_block_verification, format_pending_transaction
from postgres import get_connection_pool

""" CONSTANTS """
DEFAULT_PAGE_SIZE = 256

""" SQL QUERIES """
SQL_GET_PENDING_QUERY = """SELECT * FROM timestamps WHERE timestamp_receipt IS FALSE"""
SQL_TIMESTAMP_QUERY   = """UPDATE timestamps SET timestamp_receipt = TRUE WHERE timestamp_id = %s"""

SQL_INSERT_QUERY = """
    INSERT INTO timestamps (
        timestamp_id,
        block_id,
        origin_id,
        create_ts,
        signature,
        verification_info
    ) VALUES (%s, %s, %s, to_timestamp(%s), %s, %s)"""


def get_cursor_name():
    return str(uuid.uuid4())


def set_transaction_timestamp_proof(timestamp_id):
    sql_args = (timestamp_id,)
    execute_db_args(sql_args, SQL_TIMESTAMP_QUERY)


def insert_verification(verification_record):
    values = (
        str(uuid.uuid4()),
        verification_record["block_id"],
        verification_record["origin_id"],
        verification_record['verification_ts'],
        psycopg2.extras.Json(verification_record["signature"]),
        psycopg2.extras.Json(verification_record["verification_info"])
    )
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor()
        cur.execute(SQL_INSERT_QUERY, values)
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


# Gets timestamp_db entries with timestamp_receipt set to false
def get_pending_timestamp():
    timestamps = []
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(get_cursor_name(), cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_GET_PENDING_QUERY)
        while True:
            results = cur.fetchmany()
            if not results:
                break
            for result in results:
                timestamps.append(format_pending_transaction(result))
        cur.close()
        return timestamps
    finally:
        get_connection_pool().putconn(conn)


def execute_db_args(sql_args, query_type):
    # establish database connection with given args
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(query_type, sql_args)
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)
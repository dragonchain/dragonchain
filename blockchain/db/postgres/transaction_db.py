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

from blockchain.qry import format_transaction

from postgres import get_connection_pool

""" CONSTANTS """
DEFAULT_PAGE_SIZE = 1000
""" SQL Queries """
SQL_GET_BY_ID = """SELECT * FROM transactions WHERE transaction_id = %s"""
# adding to test querying anything
SQL_GET_ALL = """SELECT * FROM transactions"""
SQL_INSERT = """INSERT into transactions (
                            transaction_id,
                            create_ts,
                            transaction_ts,
                            business_unit,
                            family_of_business,
                            line_of_business,
                            payload,
                            signature,
                            owner,
                            transaction_type,
                            status,
                            actor,
                            entity
                          ) VALUES  (%s, to_timestamp(%s), to_timestamp(%s), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
SQL_UPDATE = """UPDATE transactions SET status = %s, block_id = %s WHERE transaction_id = %s"""
SQL_FIXATE_BLOCK = """UPDATE transactions
                            SET status='pending',
                            block_id=%s
                            WHERE status = 'new' AND
                            transaction_ts >= to_timestamp(%s) AND
                            transaction_ts <= to_timestamp(%s)"""


def get_cursor_name():
    return str(uuid.uuid4())


def get(txid):
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_GET_BY_ID, (txid,))
        result = cur.fetchone()
        cur.close()
        if result:
            result = format_transaction(result)
        return result
    finally:
        get_connection_pool().putconn(conn)


def get_all(limit=None, offset=None, **params):
    query = SQL_GET_ALL
    separator_needed = False
    if params:
        query += """ WHERE"""

    if "block_id" in params and params["block_id"]:
        query += """ block_id = %(block_id)s"""
        separator_needed = True

    if "transaction_type" in params and params["transaction_type"]:
        if separator_needed:
            query += """ AND """
        query += """ transaction_type = %(transaction_type)s"""
        separator_needed = True

    if "business_unit" in params and params["business_unit"]:
        if separator_needed:
            query += """ AND """
        query += """ business_unit = %(business_unit)s"""
        separator_needed = True

    if "family_of_business" in params and params["family_of_business"]:
        if separator_needed:
            query += """ AND """
        query+= """ family_of_business = %(family_of_business)s"""

    if "line_of_business" in params and params["line_of_business"]:
        if separator_needed:
            query += """ AND """
        query += """ line_of_business = %(line_of_business)s"""
        separator_needed = True

    if "signature" in params and params["signature"]:
        if separator_needed:
            query += """ AND """
        query += """ signature = %(signature)s"""
        separator_needed = True

    if "status" in params and params["status"]:
        if separator_needed:
            query += """ AND """
        query += """ status = %(status)s"""
        separator_needed = True

    if "owner" in params and params["owner"]:
        if separator_needed:
            query += """ AND """
        query += """ owner = %(owner)s"""
        separator_needed = True

    if "actor" in params and params["actor"]:
        if separator_needed:
            query += """ AND """
        query += """ actor = %(actor)s"""
        separator_needed = True

    if "entity" in params and params["entity"]:
        if separator_needed:
            query += """ AND"""
        query += """ entity = %(entity)s"""
        separator_needed = True

    if "create_ts" in params:
        if separator_needed:
            query += """ AND"""
        if '-' in params["create_ts"]:
            # if it is timestamp >= UNIX-epoch timecode
            if params["create_ts"].index('-') == 0:
                start_time = time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime(float(params["create_ts"][1:])))
                params["start_time"] = start_time
                query += """ create_ts >= %(start_time)s"""
            elif params["create_ts"].endswith('-'):
                end_time = time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime(float(params["create_ts"][:len(params["create_ts"])-1])))
                params["end_time"] = end_time
                query += """ create_ts <= %(end_time)s"""
            else:
                start_time = time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime(float(params["create_ts"][:params["create_ts"].index('-')])))
                end_time = time.strftime('%Y-%m-%d %H:%M:%S',  time.gmtime(float(params["create_ts"][params["create_ts"].index('-')+1:])))
                params["start_time"] = start_time
                params["end_time"] = end_time
                query += """ create_ts >= %(start_time)s AND create_ts <= %(end_time)s"""
        else:
            cur_time = time.strftime('%Y-%m-%d %H:%M:%S',  time.gmtime(float(params["create_ts"])))
            params["cur_time"] = cur_time
            query += """ create_ts = %(cur_time)s"""
        separator_needed = True

    if "transaction_ts" in params:
        print("transaction_ts")
        if separator_needed:
            query += """ AND"""
        if '-' in params["transaction_ts"]:
            # if it is timestamp >= UNIX-epoch timecode
            if params["transaction_ts"].index('-') == 0:
                start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(float(params["transaction_ts"][1:])))
                params["start_time"] = start_time
                query += """ transaction_ts >= %(start_time)s"""
            elif params["transaction_ts"].endswith('-'):
                end_time = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(float(params["create_ts"][:len(params["transaction_ts"]) - 1])))
                params["end_time"] = end_time
                query += """ transaction_ts <= %(end_time)s"""
            else:
                start_time = time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime(float(params["create_ts"][:params["transaction_ts"].index('-')])))
                end_time = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(float(params["transaction_ts"][params["create_ts"].index('-') + 1:])))
                params["start_time"] = start_time
                params["end_time"] = end_time
                query += """ transaction_ts >= %(start_time)s AND transaction_ts <= %(end_time)s"""
        else:
            cur_time = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(float(params["transaction_ts"])))
            params["cur_time"] = cur_time
            query += """ transaction_ts = %(cur_time)s"""
            separator_needed = True
            # not used but left in place to handle future params

    query += """ ORDER BY transaction_ts DESC """

    if not limit:
        limit = 10

    if limit:
        params["limit"] = limit
        query += """ LIMIT %(limit)s"""

    if offset:
        params["offset"] = offset
        query += """ OFFSET $(offset)s"""

    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(get_cursor_name(), cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(query, params)
        'An iterator that uses fetchmany to keep memory usage down'
        while True:
            results = cur.fetchmany(DEFAULT_PAGE_SIZE)
            if not results:
                break
            for result in results:
                yield format_transaction(result)
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def get_subscription_txns(criteria, block_id=None):
    """ retrieve transactions that meet given criteria and have a block_id >= minimum_block_id """
    query = SQL_GET_ALL
    query += """ WHERE """
    separator_needed = False

    if "transaction_type" in criteria:
        query += """ transaction_type = %(transaction_type)s"""
        separator_needed = True

    if "actor" in criteria:
        if separator_needed:
            query += """ AND """
        query += """ actor = %(actor)s"""
        separator_needed = True

    if "entity" in criteria:
        if separator_needed:
            query += """ AND """
        query += """ entity = %(entity)s"""
        separator_needed = True

    if "owner" in criteria:
        if separator_needed:
            query += """ AND """
        query += """ owner = %(owner)s"""
        separator_needed = True

    if block_id:
        if separator_needed:
            query += """ AND """
        query += """ block_id = %(block_id)s"""
        criteria['block_id'] = block_id  # adding for query execution vars

    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(get_cursor_name(), cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(query, criteria)
        'An iterator that uses fetchmany to keep memory usage down'
        while True:
            results = cur.fetchmany(DEFAULT_PAGE_SIZE)
            if not results:
                break
            for result in results:
                yield format_transaction(result)
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def insert_transaction(txn):
    header = txn["header"]
    sql_args = (
        header["transaction_id"],
        header["create_ts"],
        header["transaction_ts"],
        header["business_unit"],
        header["family_of_business"],
        header["line_of_business"],
        Json(txn["payload"]),
        Json(txn["signature"]),
        header["owner"],
        header["transaction_type"],
        "new",
        header.get('actor', ''),
        header.get('entity', '')
    )
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_INSERT, sql_args)
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def update_transaction(txn):
    header = txn["header"]
    sql_args = (
        header["status"],
        header["block_id"],
        str(header["transaction_id"])
    )
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_UPDATE, sql_args)
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def fixate_block(start_ts_range, end_ts_range, block_id):
    # get all tx within the previous block
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor()
        cur.execute(SQL_FIXATE_BLOCK, (block_id, start_ts_range, end_ts_range))
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)

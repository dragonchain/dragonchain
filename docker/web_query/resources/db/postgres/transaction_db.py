__author__ = 'bkite'

import psycopg2
import psycopg2.extras
from psycopg2.extras import Json
import uuid
import time

from blockchain.qry import format_transaction, \
                           format_block_verification

from postgres import get_connection_pool

DEFAULT_PAGE_SIZE = 1000

def get_cursor_name():
    return str(uuid.uuid4())


def get(txid):
    query = """SELECT * FROM transaction WHERE transaction_id = %s"""
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(query, (txid,))
        result = cur.fetchone()
        cur.close()
        if result:
            result = format_transaction(result)
        return result
    finally:
        get_connection_pool().putconn(conn)


def get_all(limit=None, offset=None, **params):
    query = """SELECT * FROM transaction"""
    multi_param = False
    if params:
        query += """ WHERE """

    if "block_id" in params:
        query += """ block_id = """ + str(params["block_id"])
        multi_param = True

    if "transaction_type" in params:
        if multi_param:
            query += """ AND """
        query += """ transaction_type = '""" + str(params["transaction_type"]) + """'"""
        multi_param = True

    if "actor" in params:
        if multi_param:
            query += """ AND """
        query += """ actor = '""" + str(params["actor"]) + """'"""
        multi_param = True

    if "entity" in params:
        if multi_param:
            query += """ AND """
        query += """ entity = '""" + str(params["entity"]) + """'"""
        multi_param = True

    if limit:
        query += """ LIMIT """ + str(limit)

    if offset:
        query += """ OFFSET """ + str(offset)

    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(get_cursor_name(), cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(query)
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
    tx_id = str(uuid.uuid4())
    insert_query = """INSERT into transaction (
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
    header = txn["header"]
    sql_args = (
        tx_id,
        int(time.time()),
        header["transaction_ts"] if "transaction_ts" in header else int(time.time()),
        header["business_unit"],
        header["family_of_business"],
        header["line_of_business"],
        Json(txn["payload"]),
        Json(txn["signature"]),
        header["owner"],
        header["transaction_type"],
        "new",
        header["actor"],
        header["entity"]
    )
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(insert_query, sql_args)
        conn.commit()
        cur.close()
        return tx_id
    finally:
        get_connection_pool().putconn(conn)


def update_transaction(txn):
    insert_query = """UPDATE transaction SET status = %s, block_id = %s WHERE transaction_id = %s"""
    header = txn["header"]
    sql_args = (
        header["status"],
        header["block_id"],
        str(header["transaction_id"])
    )
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(insert_query, sql_args)
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def fixate_block(start_ts_range, end_ts_range, block_id):
    # get all tx within the previous block
    update_query = """UPDATE transaction SET status='pending', block_id=%i WHERE status = 'new' AND create_ts >= to_timestamp(%i) AND create_ts < to_timestamp(%i)""" % (block_id, start_ts_range, end_ts_range)
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor()
        cur.execute(update_query)
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)

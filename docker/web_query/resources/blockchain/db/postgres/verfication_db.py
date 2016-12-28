__author__ = 'bkite'

import psycopg2
import psycopg2.extras
from psycopg2.extras import Json
import uuid
import time

from blockchain.qry import format_block_verification
from postgres import get_connection_pool

DEFAULT_PAGE_SIZE = 1000


def get_cursor_name():
    return str(uuid.uuid4())


def get(verification_id):
    query = """SELECT * FROM block_verification WHERE verification_id = %s"""
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(query, (verification_id,))
        result = cur.fetchone()
        cur.close()
        if result:
            result = format_block_verification(result)
        return result
    finally:
        get_connection_pool().putconn(conn)


def get_all(limit=None, offset=None, block_id=None, phase=None):
    #Build query
    query = """SELECT * FROM block_verification"""
    if block_id:
        query += """ WHERE block_id = """ + block_id

    if phase:
        if not block_id:
            query += """ WHERE """
        else:
            query += """ AND """
        query += """ phase = """ + str(phase)

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
                yield format_block_verification(result)
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def insert_verification(verification):
    insert_query = """
    INSERT INTO block_verification (
        verification_id,
        verified_ts,
        block_id,
        signature,
        owner,
        phase,
        transaction_info
    ) VALUES (%s, to_timestamp(%s), %s, %s, %s, %s, %s)"""
    values = (
        str(uuid.uuid4()),
        int(time.time()),
        verification["block_id"],
        psycopg2.extras.Json(verification["signature"]),
        verification["owner"],
        verification["phase"],
        psycopg2.extras.Json(verification["transaction_info"])
    )
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor()
        cur.execute(insert_query, values)
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)
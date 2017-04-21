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

from blockchain.qry import format_block_verification
from postgres import get_connection_pool

""" CONSTANTS """
DEFAULT_PAGE_SIZE = 1000
""" SQL QUERIES """
SQL_GET_BY_ID = """SELECT * FROM block_verifications WHERE verification_id = %s"""
SQL_GET_ALL = """SELECT * FROM block_verifications"""
SQL_GET_PRIOR_BLOCK = """SELECT * FROM block_verifications WHERE origin_id = %s AND phase = %s ORDER BY block_id DESC LIMIT 1"""
SQL_GET_ALL_REPLICATION = """SELECT * FROM block_verifications WHERE block_id = %s AND phase < %s AND origin_id = %s ORDER BY block_id DESC"""
SQL_INSERT_QUERY = """
    INSERT INTO block_verifications (
        verification_id,
        verification_ts,
        block_id,
        signature,
        origin_id,
        phase,
        verification_info
    ) VALUES (%s, to_timestamp(%s), %s, %s, %s, %s, %s)"""


def get_cursor_name():
    return str(uuid.uuid4())


def get(verification_id):
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_GET_BY_ID, (verification_id,))
        result = cur.fetchone()
        cur.close()
        if result:
            result = format_block_verification(result)
        return result
    finally:
        get_connection_pool().putconn(conn)


def get_prior_block(origin_id, phase):
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_GET_PRIOR_BLOCK, (origin_id, phase))
        result = cur.fetchone()
        cur.close()
        if result:
            result = format_block_verification(result)
        return result
    finally:
        get_connection_pool().putconn(conn)


def get_records(**params):
    """ return verification records with given criteria """
    query = SQL_GET_ALL
    query += """ WHERE"""
    separator_needed = False

    if "block_id" in params:
        query += """ block_id = %(block_id)s"""
        separator_needed = True

    if "origin_id" in params:
        if separator_needed:
            query += """ AND """
        query += """ origin_id = %(origin_id)s"""
        separator_needed = True

    if "phase" in params:
        if separator_needed:
            query += """ AND """
        query += """ phase = %(phase)s"""

    records = []

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
                records.append(format_block_verification(result))

        cur.close()
        return records
    finally:
        get_connection_pool().putconn(conn)


def get_all(limit=None, offset=None, **params):
    """ return all verification records matching given parameters """
    query = SQL_GET_ALL
    separator_needed = False
    if params:
        query += """ WHERE"""

    if "block_id" in params and params["block_id"]:
        query += """ block_id = %(block_id)s"""
        separator_needed = True

    if "phase" in params and params["phase"]:
        if separator_needed:
            query += """ AND """
        query += """ phase = %(phase)s"""
        separator_needed = True

    if "origin_id" in params and params["origin_id"]:
        if separator_needed:
            query += """ AND """
        query += """ origin_id = %(origin_id)s"""
        separator_needed = True

    if "min_block_id" in params and params["min_block_id"]:
        if separator_needed:
            query += """ AND """
        query += """ block_id >= %(min_block_id)s"""
        separator_needed = True

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
                yield format_block_verification(result)
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def get_all_replication(block_id, phase, origin_id):
    """ queries for records matching given block_id, having phase less than given phase,
        and matching origin_id. This is used for retrieving verification records at lower
        phases that match the higher phase record in question. """

    records = []
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(get_cursor_name(), cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_GET_ALL_REPLICATION, (block_id, phase, origin_id))
        'An iterator that uses fetchmany to keep memory usage down'
        while True:
            results = cur.fetchmany(DEFAULT_PAGE_SIZE)
            if not results:
                break
            for result in results:
                records.append(format_block_verification(result))

        cur.close()
        return records
    finally:
        get_connection_pool().putconn(conn)


def insert_verification(verification_record, verification_id=None):
    if not verification_id:
        verification_id = str(uuid.uuid4())
    values = (
        verification_id,
        verification_record['verification_ts'],
        verification_record["block_id"],
        psycopg2.extras.Json(verification_record["signature"]),
        verification_record["origin_id"],
        verification_record["phase"],
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

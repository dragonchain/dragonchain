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
import time

from blockchain.qry import format_node

from postgres import get_connection_pool
import uuid

""" CONSTANTS """
# TODO: CONST for interval time, limit - import from file
DEFAULT_PAGE_SIZE = 1000
BIT_LENGTH = 5
MAX_CONN_LIMIT = 5
""" SQL Queries """
SQL_GET_BY_ID = """SELECT * FROM nodes WHERE node_id = %s"""
SQL_GET_ALL = """SELECT * FROM nodes"""
SQL_GET_BY_PHASE = """SELECT * FROM nodes 
                            WHERE 
                            phases & %s::bit(%s) != 0::bit(%s) AND 
                            connection_attempts IS NULL 
                            ORDER BY priority_level ASC, latency DESC 
                            LIMIT %s"""
SQL_GET_UNREGISTERED_NODES = """SELECT * FROM nodes 
                            WHERE last_conn_attempt_ts IS NULL OR 
                            last_conn_attempt_ts < NOW() - INTERVAL '7 days' AND 
                            start_conn_ts IS NULL AND 
                            last_activity_ts < NOW() - INTERVAL '7 days' 
                            ORDER BY priority_level ASC, last_conn_attempt_ts ASC, connection_attempts ASC 
                            LIMIT %s"""
SQL_INSERT = """INSERT into nodes (
                            node_id,
                            create_ts,
                            node_owner,
                            host,
                            port,
                            phases,
                            latency,
                            pass_phrase
                          ) VALUES  (%s, to_timestamp(%s), %s, %s, %s, %s::BIT(5), %s, %s)"""
SQL_UPDATE_CON_START = """UPDATE nodes SET start_conn_ts = to_timestamp(%s), last_activity_ts = to_timestamp(%s), pass_phrase = %s, connection_attempts = NULL, last_conn_attempt_ts = NULL WHERE node_id = %s"""
SQL_UPDATE_CON_ATTEMPTS = """UPDATE nodes SET connection_attempts = COALESCE(connection_attempts, 0) + 1, last_conn_attempt_ts = to_timestamp(%s), start_conn_ts = NULL WHERE node_id = %s"""
SQL_UPDATE_CON_ACTIVITY = """UPDATE nodes SET last_activity_ts = to_timestamp(%s), latency = %s, last_conn_attempt_ts = NULL, connection_attempts = NULL WHERE node_id = %s"""
SQL_FAILED_PING = """UPDATE nodes SET start_conn_ts = NULL, latency = NULL WHERE node_id = %s"""
SQL_RESET_ALL = """UPDATE nodes SET start_conn_ts = NULL, connection_attempts = NULL, last_conn_attempt_ts = NULL, latency = NULL """
SQL_RESET_START = """UPDATE nodes SET start_conn_ts = NULL WHERE node_id = %s """


def get(node_id):
    """ query for network node that matches given node id """
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_GET_BY_ID, (node_id,))
        result = cur.fetchone()
        cur.close()
        if result:
            result = format_node(result)
        return result
    finally:
        get_connection_pool().putconn(conn)


def insert_node(node):
    """ insert given network node into table."""
    node_id = node.node_id
    sql_args = (
        node_id,
        int(time.time()),  # node creation time
        node.owner,
        node.host,
        node.port,
        node.phases,  # phases provided in binary
        node.latency,
        node.pass_phrase  # used for Thrift network auth
    )
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_INSERT, sql_args)
        conn.commit()
        cur.close()
        return node_id
    finally:
        get_connection_pool().putconn(conn)


def get_cursor_name():
    return str(uuid.uuid4())


def get_by_phase(phases, limit=None):
    """
        query for all nodes that provide services for the given phases (bitwise and)
        e.g. 01001 (phase 1 and 4) will return all nodes that provide either phase 1, 4 or both
    """
    if not limit or limit > MAX_CONN_LIMIT:
        limit = MAX_CONN_LIMIT

    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(get_cursor_name(), cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_GET_BY_PHASE, (phases, BIT_LENGTH, BIT_LENGTH, limit))
        'An iterator that uses fetchmany to keep memory usage down'
        while True:
            results = cur.fetchmany(DEFAULT_PAGE_SIZE)
            if not results:
                break
            for result in results:
                yield format_node(result)
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def get_unregistered_nodes(limit=None):
    """ query for all nodes that are currently unconnected """

    #  should possibly be based upon total unregistered/non-connected nodes and how often this is executed
    # TODO: base time interval based on number of attempts (fibonacci series?)

    if not limit or limit > MAX_CONN_LIMIT:
        limit = MAX_CONN_LIMIT

    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(get_cursor_name(), cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_GET_UNREGISTERED_NODES, (limit,))
        'An iterator that uses fetchmany to keep memory usage down'
        while True:
            results = cur.fetchmany(DEFAULT_PAGE_SIZE)
            if not results:
                break
            for result in results:
                yield format_node(result)
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def update_con_start(node):
    # update connection start time. reset attempts and last attempt time
    sql_args = (
        int(time.time()),  # connection start time
        int(time.time()),  # last activity time
        node.pass_phrase,
        node.node_id)
    execute_db_args(sql_args, SQL_UPDATE_CON_START)


def update_con_attempts(node):
    """ increment connection attempts, update last connection attempt time. reset conn success """
    sql_args = (
        int(time.time()),  # last attempt time
        node.node_id)
    execute_db_args(sql_args, SQL_UPDATE_CON_ATTEMPTS)


def update_con_activity(node):
    """ update node latency and time of last activity """
    sql_args = (
        int(time.time()),  # activity time
        node.latency,      # node latency
        node.node_id)
    execute_db_args(sql_args, SQL_UPDATE_CON_ACTIVITY)


def update_failed_ping(node):
    """ reset connection start time and latency when registered node fails to ping """
    sql_args = (node.node_id,)
    execute_db_args(sql_args, SQL_FAILED_PING)


def reset_data():
    """ reset start_conn, latency, conn_attempts, last_attempt_ts on start up (used for testing) """
    sql_args = (None,)  # last attempt time
    # FIXME: No args needed
    execute_db_args(sql_args, SQL_RESET_ALL)


def reset_start_time(node):
    """ reset start_conn_ts to null """
    sql_args = (node.node_id,)
    execute_db_args(sql_args, SQL_RESET_START)


def execute_db_args(sql_args, query_type):
    """ establish database connection with given args """
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(query_type, sql_args)
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)

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

"""
                ***** client-side subscription dao ******
Stores subscription info for the subscriber node when a subscription transaction is received.
data stored:
 - the subscription node's id, owner, host, and port.
 - the subscription criteria to be met.
 - the subscription create timestamp.
 - the status of the subscription (i.e. approved, pending, etc.).
subscription data is queried based on synchronization periods. if a sub has not been called
since a time greater than its synchronization period, it will be queried.
"""

__author__ = "Joe Roets, Brandon Kite, Dylan Yelton, Michael Bachtel"
__copyright__ = "Copyright 2016, Disney Connected and Advanced Technologies"
__license__ = "Apache"
__version__ = "2.0"
__maintainer__ = "Joe Roets"
__email__ = "joe@dragonchain.org"


import psycopg2
import psycopg2.extras

from blockchain.qry import format_subscription

from postgres import get_connection_pool

import uuid

""" CONSTANTS """
DEFAULT_PAGE_SIZE = 1000
""" SQL Queries """
SQL_GET_ALL = """SELECT * FROM sub_to WHERE (CURRENT_TIMESTAMP - last_time_called) > (synchronization_period * '1 sec'::interval) ORDER BY status LIMIT %s"""
SQL_INSERT = """INSERT into sub_to (
                    subscription_id,
                    subscribed_node_id,
                    node_owner,
                    host,
                    port,
                    criteria,
                    create_ts,
                    status
                ) VALUES (%s, %s, %s, %s, %s, %s, to_timestamp(%s), %s)"""


def insert_subscription(subscription, subscription_id=None):
    """ insert given subscription into database """
    if not subscription_id:
        subscription_id = str(uuid.uuid4())
    values = (
        subscription_id,  # subscription uuid pk
        subscription['subscribed_node_id'],  # id of subscription node
        subscription['node_owner'],  # owner of subscription node
        subscription['host'],  # subscription node's host
        subscription['port'],  # subscription node's port
        psycopg2.extras.Json(subscription['criteria']),  # criteria to be met by subscription
        subscription['create_ts'],  # subscription creation time
        "pending"  # subscription status
    )
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor()
        cur.execute(SQL_INSERT, values)
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def get_all(limit=None):
    """ query for all subscriptions that have passed due synchronization periods """

    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(get_cursor_name(), cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_GET_ALL, (limit, ))
        'An iterator that uses fetchmany to keep memory usage down'
        while True:
            results = cur.fetchmany(DEFAULT_PAGE_SIZE)
            if not results:
                break
            for result in results:
                yield format_subscription(result)
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def get_cursor_name():
    return str(uuid.uuid4())

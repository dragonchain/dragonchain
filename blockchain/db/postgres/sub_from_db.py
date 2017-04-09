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
                ***** server-side subscription dao ******
Stores subscription info from subscribers (client nodes) for the data provider.
data stored:
 - node id of subscriber (client)
 - criteria to be met by subscription
 - phase criteria to be met by subscription
 - public key of subscriber (client)
 - subscription create timestamp
subscription data is queried based on subscriber ids and phase criteria.
"""

__author__ = "Joe Roets, Brandon Kite, Dylan Yelton, Michael Bachtel"
__copyright__ = "Copyright 2016, Disney Connected and Advanced Technologies"
__license__ = "Apache"
__version__ = "2.0"
__maintainer__ = "Joe Roets"
__email__ = "joe@dragonchain.org"


import psycopg2
import psycopg2.extras

from blockchain.qry import format_subscriber
from postgres import get_connection_pool

import uuid


""" CONSTANTS """
DEFAULT_PAGE_SIZE = 1000
""" SQL Queries """
SQL_GET_BY_ID = """SELECT * FROM sub_from WHERE subscriber_id = %s"""
SQL_GET_ALL_BY_PHASE = """SELECT * FROM sub_from WHERE phase_criteria = %s"""
SQL_INSERT = """INSERT into sub_from (
                    subscriber_id,
                    criteria,
                    phase_criteria,
                    subscriber_public_key,
                    create_ts
                ) VALUES (%s, %s, %s, %s, to_timestamp(%s)) """


def insert_subscription(subscriber_id, criteria, phase_criteria, subscriber_public_key, create_ts):
    """
    insert given subscription into database
    param subscriber_id: id of subscribing node
    param criteria: json structured data of criteria to be met by the subscription node
    param phase_criteria: subscriber requests data up to this phase
    param create_ts: time subscription was created
    """
    values = (
        subscriber_id,
        psycopg2.extras.Json(criteria),
        phase_criteria,
        subscriber_public_key,
        create_ts
    )
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor()
        cur.execute(SQL_INSERT, values)
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def get(subscriber_id):
    """ query for subscription matching given subscriber_id """
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_GET_BY_ID, (subscriber_id, ))
        result = cur.fetchone()
        cur.close()
        if result:
            result = format_subscriber(result)
        return result
    finally:
        get_connection_pool().putconn(conn)


def get_by_phase_criteria(phase):
    """ retrieve subscriptions with phase criteria that match given phase """
    subscriptions = []
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(get_cursor_name(), cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_GET_ALL_BY_PHASE, (phase, ))
        'An iterator that uses fetchmany to keep memory usage down'
        while True:
            results = cur.fetchmany(DEFAULT_PAGE_SIZE)
            if not results:
                break
            for result in results:
                subscriptions.append(format_subscriber(result))
        cur.close()
        return subscriptions
    finally:
        get_connection_pool().putconn(conn)


def get_cursor_name():
    return str(uuid.uuid4())
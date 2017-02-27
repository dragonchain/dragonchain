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
from postgres import get_connection_pool

from blockchain.qry import format_backlog

""" CONSTANTS """
DEFAULT_PAGE_SIZE = 1000
SQL_GET_BY_ID = """SELECT * FROM sub_vr_backlog WHERE block_id = %s"""
GET_BACKLOGS = """SELECT * FROM sub_vr_backlog"""
SQL_INSERT_QUERY = """INSERT INTO sub_vr_backlog (
                                  transfer_id,
                                  client_id,
                                  block_id
                                  ) VALUES (%s, %s, %s)"""


def insert_backlog(client_id, block_id):
    """
    insert new backlog
     param client_id: id of subscribing node
     param block_id: block id of backlog
    """
    values = (
        str(uuid.uuid4()),  # transfer_id PK
        client_id,
        block_id
    )
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor()
        cur.execute(SQL_INSERT_QUERY, values)
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def get_backlogs(block_id):
    """ check if backlog exists for given block id """
    back_logs = []
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_GET_BY_ID, (block_id,))
        'An iterator that uses fetchmany to keep memory usage down'
        while True:
            results = cur.fetchmany(DEFAULT_PAGE_SIZE)
            if not results:
                break
            for result in results:
                back_logs.append(format_backlog(result))
        cur.close()
        return back_logs
    finally:
        get_connection_pool().putconn(conn)


def get_cursor_name():
    return str(uuid.uuid4())

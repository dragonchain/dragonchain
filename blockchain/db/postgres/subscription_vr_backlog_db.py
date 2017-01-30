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
from psycopg2.extras import Json
from postgres import get_connection_pool

""" CONSTANTS """
DEFAULT_PAGE_SIZE = 1000
GET_BACKLOGS = """SELECT * FROM subscription_vr_backlog"""
SQL_INSERT_QUERY = """INSERT INTO subscription_vr_backlog (
                                  transfer_id,
                                  subscription_id,
                                  client_id,
                                  block_id,
                                  completion_criteria
                                  ) VALUES (%s, %s, %s, %s, %s)"""


def insert_backlog(subscription_id, client_id, block_id, completion_criteria):
    values = (
        str(uuid.uuid4()),  # transfer_id PK
        subscription_id,
        client_id,
        block_id,
        Json(completion_criteria)
    )
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor()
        cur.execute(SQL_INSERT_QUERY, values)
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def get_cursor_name():
    return str(uuid.uuid4())

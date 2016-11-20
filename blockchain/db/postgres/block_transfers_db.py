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

import psycopg2
import psycopg2.extras
import uuid

from blockchain.qry import format_verification_record

from postgres import get_connection_pool

""" CONSTANTS """
DEFAULT_PAGE_SIZE = 1000
GET_VERIFIED_RECORDS = """SELECT verification_id from block_transfers"""
SET_MARK_RECORD = """UPDATE block_transfers SET sent = %s"""


def get_verification_records(ver_id):
    if ver_id:
        query = GET_VERIFIED_RECORDS
        query += """ WHERE verification_id = """ + ver_id
        query += """ AND sent = 0 """
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
                    yield format_verification_record(result)
            cur.close()
        finally:
            get_connection_pool().putconn(conn)


def set_verfication_sent(ver_id, transfer_to):
    query = SET_MARK_RECORD
    query += """"WHERE verification_id = """ + ver_id
    query += """ transfer_to = """"" + transfer_to
    query += """ send = B'1' """

def get_cursor_name():
    return str(uuid.uuid4())

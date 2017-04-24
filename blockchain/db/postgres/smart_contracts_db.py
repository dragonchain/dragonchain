"""
Copyright 2017, Dragonchain Foundation

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
__copyright__ = "Copyright 2017, Dragonchain Foundation"
__license__ = "Apache"
__version__ = "2.0"
__maintainer__ = "Joe Roets"
__email__ = "joe@dragonchain.org"


import psycopg2
import psycopg2.extras

from postgres import get_connection_pool
import uuid

from blockchain.qry import format_sc


""" CONSTANTS """
DEFAULT_PAGE_SIZE = 1000
""" SQL Queries """
SQL_GET_APPROVED = """SELECT * FROM smart_contracts WHERE status = 'approved'"""
SQL_INSERT = """INSERT into smart_contracts (
                   sc_id,
                   sc_class,
                   smart_contract,
                   sc_key,
                   criteria,
                   test,
                   requirements,
                   version,
                   status
               ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""


def insert_sc(sc, sc_class, sc_key):
    """
    insert given smart contract into database
    :param sc: smart contract payload
    :param sc_class: type of smart contract being run
    :param sc_key: dictionary key
    """
    values = (
        str(uuid.uuid4()),  # uuid pk
        sc_class,
        sc['smart_contract'][sc_class],  # code to be run
        sc_key,  # dictionary key
        sc['criteria'],  # criteria (i.e. transaction type)
        sc['test'],  # unit test
        sc['requirements'],  # required libraries
        sc['version'],  # current version
        "approved"  # sc status
    )
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor()
        cur.execute(SQL_INSERT, values)
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def get_cursor_name():
    return str(uuid.uuid4())


def get_all():
    """ query for all approved smart contracts """

    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(get_cursor_name(), cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_GET_APPROVED)
        'An iterator that uses fetchmany to keep memory usage down'
        while True:
            results = cur.fetchmany(DEFAULT_PAGE_SIZE)
            if not results:
                break
            for result in results:
                yield format_sc(result)
        cur.close()
    finally:
        get_connection_pool().putconn(conn)

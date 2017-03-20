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


from postgres import get_connection_pool
from psycopg2.extras import Json
import uuid


""" CONSTANTS """
DEFAULT_PAGE_SIZE = 1000
""" SQL Queries """
SQL_GET_ALL = """SELECT * FROM smart_contracts"""
SQL_INSERT = """INSERT into smart_contracts (
                   sc_id,
                   smart_contract,
                   transaction_type,
                   criteria,
                   test,
                   requirements,
                   version
               ) VALUES (%s, %s, %s, %s, %s, %s, %s)"""


def insert_sc(sc, sc_type, txn_type):
    """
    insert given smart contract into database
    :param sc: smart contract payload
    :param sc_type: type of smart contract being run
    :param txn_type: transaction type
    """
    values = (
        str(uuid.uuid4()),  # uuid pk
        sc['smart_contract'][sc_type],  # code to be run
        txn_type,  # transaction type
        Json(sc['criteria']),  # criteria (i.e. transaction type)
        sc['test'],  # unit test
        sc['requirements'],  # required libraries
        sc['version']  # current version
    )
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor()
        cur.execute(SQL_INSERT, values)
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)
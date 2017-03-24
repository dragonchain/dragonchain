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

__author__ = "Joe Roets, Brandon Kite, Dylan Yelton, Michael Bachtel, Steve Owens"
__copyright__ = "Copyright 2016, Disney Connected and Advanced Technologies"
__license__ = "Apache"
__version__ = "2.0"
__maintainer__ = "Joe Roets"
__email__ = "joe@dragonchain.org"

import psycopg2.extras
import uuid
import copy
from psycopg2.extras import Json
from blockchain.db.postgres.utilities.sql_clause_builder import SQLClauseBuilder
from blockchain.db.postgres.utilities.sql_query_helper import SQLQueryHelper

from blockchain.qry import format_transaction
from postgres import get_connection_pool

""" SQL Queries """
SQL_GET_BY_ID = """SELECT * FROM transactions WHERE transaction_id = %s"""
# adding to test querying anything
SQL_GET_ALL = """SELECT * FROM transactions"""
SQL_INSERT = """INSERT into transactions (
                            transaction_id,
                            create_ts,
                            transaction_ts,
                            business_unit,
                            family_of_business,
                            line_of_business,
                            payload,
                            signature,
                            owner,
                            transaction_type,
                            status,
                            actor,
                            entity
                          ) VALUES  (%s, to_timestamp(%s), to_timestamp(%s), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
SQL_UPDATE = """UPDATE transactions SET status = %s, block_id = %s WHERE transaction_id = %s"""
SQL_FIXATE_BLOCK = """UPDATE transactions SET status='pending', block_id=%i WHERE status = 'new' AND transaction_ts >= to_timestamp(%i) AND transaction_ts <= to_timestamp(%i)"""

builder = SQLClauseBuilder()
query_helper = SQLQueryHelper()

def get(self, txid):
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_GET_BY_ID, (txid,))
        result = cur.fetchone()
        cur.close()
        if result:
            result = format_transaction(result)
        return result
    finally:
        get_connection_pool().putconn(conn)
        
    
def get_all(self, limit = 10, offset=None, **params):
    query = SQL_GET_ALL
    if params:
        query +=  " WHERE "
        valid_string_values = ['block_id', 'transaction_type',
                    'business_unit', 'family_of_business',
                    'line_of_business', 'signature',
                    'status', 'owner', 'actor', 'entity']
        valid_time_range_values = ['create_ts', 'transaction_ts']
    
        string_constraints = builder.build(" AND ","string", 
                                       valid_string_values, params)
        time_constraints = builder.build(" AND ", "time_range", 
                                     valid_time_range_values, params)
        clauses = []
        if string_constraints:
            clauses.append(string_constraints)
        if time_constraints:
            clauses.append(time_constraints)
            
        if clauses:
            query += " AND " + " AND ".join(clauses)

    if params["transaction_ts"]:   
        query += " ORDER BY transaction_ts DESC "
    query += """ LIMIT """ + str(limit)
    if offset:
        query += """ OFFSET """ + str(offset)

    return query_helper.run_query(query, format_transaction)


def get_subscription_txns(self, criteria, block_id=None):
    """ retrieve transactions that meet given criteria and have a block_id >= minimum_block_id """
    if not criteria and not block_id:
        raise ValueError("No criteria specified for the query.")
    query = SQL_GET_ALL 
    allowed_params = [ 'transaction_type', 'actor', 
                      'entity', 'owner', 'block_id']
    
    params = criteria.copy()
    if block_id:
        params['block_id'] = block_id
        
    query += " WHERE " 
    query += builder.build_parameter_list(" AND ", allowed_params, params)
    return query_helper.query_for_results(query, format_transaction)



def insert_transaction(txn):
    header = txn["header"]
    sql_args = (
        header["transaction_id"],
        header["create_ts"],
        header["transaction_ts"],
        header["business_unit"],
        header["family_of_business"],
        header["line_of_business"],
        Json(txn["payload"]),
        Json(txn["signature"]),
        header["owner"],
        header["transaction_type"],
        "new",
        header.get('actor', ''),
        header.get('entity', '')
    )
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_INSERT, sql_args)
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def update_transaction(txn):
    header = txn["header"]
    sql_args = (
        header["status"],
        header["block_id"],
        str(header["transaction_id"])
    )
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(SQL_UPDATE, sql_args)
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)


def fixate_block(start_ts_range, end_ts_range, block_id):
    # get all tx within the previous block
    update_query = SQL_FIXATE_BLOCK % (block_id, start_ts_range, end_ts_range)
    conn = get_connection_pool().getconn()
    try:
        cur = conn.cursor()
        cur.execute(update_query)
        conn.commit()
        cur.close()
    finally:
        get_connection_pool().putconn(conn)

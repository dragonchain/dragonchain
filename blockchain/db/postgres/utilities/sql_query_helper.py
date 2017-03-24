"""
Created on Mar 23, 2017
Copyright 2017 Disney Connected and Advanced Technologies

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
__author__ = "Steve Owens"
__copyright__ = "Copyright 2017, Disney Connected and Advanced Technologies"
__license__ = "Apache"
__version__ = "2.0"
__maintainer__ = "Steve Owens"
__email__ = "steve098501@gmail.com"

import psycopg2.extras
import uuid
from blockchain.db.postgres.postgres import get_connection_pool


""" CONSTANTS """
DEFAULT_PAGE_SIZE = 1000

def get_cursor_name():
    return str(uuid.uuid4())

class SQLQueryHelper(object):
    """
    This module encapsulates the conversion of a set of keyword arguments into a postgresql where clause.
    The intent is to enable the replacement of long chains of code of the form

    if "block_id" in params:
        query += ''' block_id = ''' + str(params['block_id'])
        separator_needed = True

    if "transaction_type" in params:
        if separator_needed:
            query += ''' AND '''
        query += " transaction_type = '" + str(params["transaction_type"]) + "'"
        separator_needed = True
        
        ...
        ...
        
    With a more concise expression
    """
    __valid_types = ["string", "time_range"]
    
    def __init__(self):
        '''
        Constructor takes a joining operator which is an element of
        the set { 'AND', 'OR', ','} and joins the elements of 
        field_values into equality / assignment statements.
        '''
        
        
    def query_for_records(self, query, transform_function, **params):
        """
        Runs the given parameterized query passing query and **params to 
        cursor.execute(query, params)  it accumulates the result set in 
        an array after applying transform_function to each result.
        When all results have been accumulated the array is returned.
        """       
        conn = get_connection_pool().getconn()
        try:
            cur = conn.cursor(get_cursor_name(), cursor_factory=psycopg2.extras.DictCursor)
            cur.execute(query, params)
            records = []
            results = cur.fetchmany(DEFAULT_PAGE_SIZE)
            while results:
                for result in results:
                    records.append(transform_function(result))
                results = cur.fetchmany(DEFAULT_PAGE_SIZE)
            cur.close()
            return records
        finally:
            get_connection_pool().putconn(conn)
        
        
    def query_for_one_record(self, query, transform_function):
        """
        Runs the given query and applies the given transform_function to
        the result.  The transform function takes a single element 
        of the result of cur.fetchone()
        """
        conn = get_connection_pool().getconn()
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute(query)
            result = cur.fetchone()
            cur.close()
            if result:
                result = transform_function(result)
            return result
        finally:
            get_connection_pool().putconn(conn)
        
        
    def query_for_results(self, query, transform_function):
        """
        Executes a select query and returns a generator which
        applies the transform_function to each result in the
        query result set produced by the generator
        """
        conn = get_connection_pool().getconn()
        try:
            cur = conn.cursor(get_cursor_name(), cursor_factory=psycopg2.extras.DictCursor)
            cur.execute(query)
            'An iterator that uses fetchmany to keep memory usage down'
            results = cur.fetchmany(DEFAULT_PAGE_SIZE)
            while results:
                for result in results:
                    yield transform_function(result)
                results = cur.fetchmany(DEFAULT_PAGE_SIZE)
            cur.close()
        finally:
            get_connection_pool().putconn(conn)
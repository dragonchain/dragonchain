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

from psycopg2.pool import ThreadedConnectionPool
import os

"""
Define environment variables
"""
ENV_MIN_CONNECTIONS = "BLOCKCHAIN_DB_MIN_CONNECTIONS"
ENV_MAX_CONNECTIONS = "BLOCKCHAIN_DB_MAX_CONNECTIONS"
ENV_DATABASE_NAME = "BLOCKCHAIN_DB_NAME"
ENV_HOSTNAME = "BLOCKCHAIN_DB_HOSTNAME"
ENV_DB_USERNAME = "BLOCKCHAIN_DB_USERNAME"
ENV_DB_PASSWORD = "BLOCKCHAIN_DB_PASSWORD"
ENV_DB_PORT = "BLOCKCHAIN_DB_PORT"

"""
Define configuration defaults
"""
DEFAULT_MIN_CONNECTIONS = 1
DEFAULT_MAX_CONNECTIONS = 10
DEFAULT_DB_NAME = "blockchain"
DEFAULT_DB_HOST = "localhost"
DEFAULT_DB_PORT = 5432
DEFAULT_DB_USERNAME = "blocky"
DEFAULT_DB_PASSWORD = None

"""
Setup database connection pool parameters
"""
min_connections = os.getenv(ENV_MIN_CONNECTIONS, DEFAULT_MIN_CONNECTIONS)
max_connections = os.getenv(ENV_MAX_CONNECTIONS, DEFAULT_MAX_CONNECTIONS)

database = os.getenv(ENV_DATABASE_NAME, DEFAULT_DB_NAME)
host = os.getenv(ENV_HOSTNAME, DEFAULT_DB_HOST)
port = os.getenv(ENV_DB_PORT, DEFAULT_DB_PORT)
username = os.getenv(ENV_DB_USERNAME, DEFAULT_DB_USERNAME)
password = os.getenv(ENV_DB_PASSWORD, DEFAULT_DB_PASSWORD)

"""
Create connection pool
"""
connection_pool = ThreadedConnectionPool(min_connections, max_connections,
                                         database=database,
                                         host=host,
                                         port=port,
                                         user=username,
                                         password=password)


def get_connection_pool():
    """Get the globally instantiated connection pool"""
    return connection_pool


def cleanup():
    """ Call to dispose connections """
    connection_pool.closeall()
__author__ = 'bkite'

from psycopg2.pool import ThreadedConnectionPool
import os

"""
Define environment variables
"""
ENV_MIN_CONNECTIONS = "BLOCKCHAIN_DB_MIN_CONNECTIONS"
ENV_MAX_CONNECTIONS = "BLOCKCHAIN_DB_MAX_CONNECTIONS"
ENV_DATABASE_NAME = "BLOCKCHAIN_DB_NAME"
ENV_HOSTNAME = "BLOCKCHAIN_DB_HOSTNAME"

"""
Define configuration defaults
"""
DEFAULT_MIN_CONNECTIONS = 1
DEFAULT_MAX_CONNECTIONS = 10
DEFAULT_DB_NAME = "blockchain"
DEFAULT_DB_HOST = "localhost"

"""
Setup database connection pool parameters
"""
min_connections = os.getenv(ENV_MIN_CONNECTIONS, DEFAULT_MIN_CONNECTIONS)
max_connections = os.getenv(ENV_MAX_CONNECTIONS, DEFAULT_MAX_CONNECTIONS)
database = os.getenv(ENV_DATABASE_NAME, DEFAULT_DB_NAME)
host = os.getenv(ENV_HOSTNAME, DEFAULT_DB_HOST)

"""
Create connection pool
"""
connection_pool = ThreadedConnectionPool(min_connections, max_connections,
                                         database=database,
                                         host=host)

def get_connection_pool():
    """Get the globally instantiated connection pool"""
    return connection_pool


def close_connection_pool():
    """ Call to dispose connections """
    connection_pool.closeall()
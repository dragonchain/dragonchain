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


""" only used for manually inserting data into nodes table """
from blockchain.db.postgres import network_db as net_dao
from blockchain.network import Node

import os

import uuid

import argparse


def load_required_nodes(owner, host, port, phases, node_id=str(uuid.uuid4())):
    """
    manually insert network node into database
    Args:
        owner: node owner
        host: node host
        port: node port
        phases: node phases provided
        node_id: node uuid pk
    """
    node = Node(node_id, owner, host, port, phases)
    net_dao.insert_node(node)
    print('inserted node into database ' + os.environ.get('BLOCKCHAIN_DB_NAME') + " " + node.node_id)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process node data.')
    parser.add_argument('--owner', default="TEST_OWNER")
    parser.add_argument('--host', default="localhost")
    parser.add_argument('-p', '--port')
    parser.add_argument('--phases', default="00001")

    args = vars(parser.parse_args())

    owner = args['owner']
    host = args['host']
    port = args['port']
    phases = args['phases']

    load_required_nodes(owner, host, port, phases)

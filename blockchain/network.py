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


"""
Service task to handle connection management & RMI
"""
import sys
import os
from yaml import load

import json

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from blockchain.db.postgres import network_db as net_dao

import gen.messaging.BlockchainService as BlockchainService
import gen.messaging.ttypes as message_types
import db.postgres.postgres as pg

from blockchain.util.thrift_conversions import convert_to_thrift_transaction, \
                                               convert_to_thrift_record, \
                                               thrift_record_to_dict, \
                                               thrift_transaction_to_dict

from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

import logging
import time
import uuid

sys.path.append('gen')


DEFAULT_PORT = 9080

NODE_ID_PROPERTY_KEY = 'node_id'
OWNER_PROPERTY_KEY = 'owner'
BUSINESS_PROPERTY_KEY = 'business'
LOCATION_PROPERTY_KEY = 'deploy_location'
PUB_TRANS_PROPERTY_KEY = 'public_transmission'
INBOUND_TIMEOUT = 30  # seconds

RECORD = 'record'
VERIFICATION_RECORD = 'verification_record'
VERIFICATION_INFO = 'verification_info'

PHASE_1_NODE = 0b00001
PHASE_2_NODE = 0b00010
PHASE_3_NODE = 0b00100
PHASE_4_NODE = 0b01000
PHASE_5_NODE = 0b10000

DATABASE_NAME = os.getenv(pg.ENV_DATABASE_NAME, pg.DEFAULT_DB_NAME)

CONFIG_FILE = '../configs/' + DATABASE_NAME + '.yml'

LOG_FILE = '../logs/' + DATABASE_NAME + '.log'
open(LOG_FILE, 'w').close()  # reset log file


def logger(name="network-manager"):
    logging.basicConfig(filename=LOG_FILE, level=logging.INFO)
    logging.getLogger("apscheduler.scheduler").setLevel('WARNING')
    logging.getLogger("apscheduler.executors").setLevel('WARNING')
    logging.getLogger('apscheduler.scheduler').propagate = False
    return logging.getLogger(name)


def format_error(category, msg):
    return json.dumps({"error": {"type": category, "details": msg}})


# TODO: add public-key attr.
class Node(object):
    def __init__(self, node_id, node_owner, host, port, phases):
        self.node_id = node_id
        self.owner = node_owner
        self.host = host
        self.port = str(port)
        self.phases = int(phases, 2)
        self.latency = 0
        self.client = None
        self.transport = None
        self.pass_phrase = None
        self.connected = False
        # TODO: enter as cmd line arg
        self.public_key = None
        self.proof = None

    def __eq__(self, other):
            return hash(self.node_id) == hash(other.node_id)

    def __hash__(self):
        return hash(self.node_id)


class ConnectionManager(object):
    def __init__(self, host, port, phases, processing_node=None, max_inbound_connections=50, max_outbound_connections=50):
        # TODO consider to change phases back to array of ints and translate w/in the DB interface
        net_dao.reset_data()  # TEMP FOR TESTING
        self.this_node = message_types.Node()
        self.host = host
        self.port = port
        self.business = None
        self.deploy_location = None
        # phase_type => {nodes} (dictionary of connected nodes)
        self.peer_dict = {}
        self.config = None
        # list of connected nodes
        self.connections = set()
        self.phases = int(phases)
        self.processing_node = processing_node
        """ Load configured nodelist """
        logger().info('loading network config...')
        self.load_config()
        logger().info('scheduling network tasks...')
        self.schedule_tasks()

        self.max_inbound_connections = max_inbound_connections
        self.max_outbound_connections = max_outbound_connections

        # BLOCKING
        logger().info('Starting RMI service handler...')

        # if testing network only without processing
        if processing_node is None:
            self.start_service_handler()

    def load_config(self):
        if self.config is None:
            self.config = load(file(CONFIG_FILE))

        self.business = self.config[BUSINESS_PROPERTY_KEY]
        self.deploy_location = self.config[LOCATION_PROPERTY_KEY]

        # set public_transmission dictionary from yml config
        if self.processing_node:
            self.processing_node.public_transmission = self.config[PUB_TRANS_PROPERTY_KEY]

        self.this_node.host = self.host
        self.this_node.port = int(self.port)
        self.this_node.owner = self.config[OWNER_PROPERTY_KEY]
        self.this_node.node_id = self.config[NODE_ID_PROPERTY_KEY]
        self.this_node.phases = int(self.phases)

    def start_service_handler(self):
        handler = BlockchainServiceHandler(self)
        processor = BlockchainService.Processor(handler)
        transport = TSocket.TServerSocket(port=self.port)
        tfactory = TTransport.TBufferedTransportFactory()
        pfactory = TBinaryProtocol.TBinaryProtocolFactory()
        server = TServer.TThreadedServer(processor, transport, tfactory, pfactory)
        logger().info('starting server...')
        server.serve()
        logger().info('server started.')

    def schedule_tasks(self):
        scheduler = BackgroundScheduler()

        scheduler.add_job(self.refresh_registered, CronTrigger(second='*/5'))
        scheduler.add_job(self.refresh_unregistered, CronTrigger(second='*/60'))
        scheduler.add_job(self.connect, CronTrigger(second='*/5'))
        scheduler.start()

    def refresh_registered(self):
        """ - gathering latency and health for connected (registered) nodes
            - gathering "peers of peers"
        """
        logger().info('connection refresh')
        if self.peer_dict.values():
            for peer in self.connections:
                if self.calc_latency(peer):
                    net_dao.update_con_activity(peer)  # update node health
                    peers_discovered = peer.client.get_peers()
                    for thrift_node in peers_discovered:  # converting to network node and updating database
                        converted_node = Node(thrift_node.node_id, thrift_node.owner, thrift_node.host,
                                              str(thrift_node.port), bin(thrift_node.phases))
                        try:
                            net_dao.insert_node(converted_node)
                        except Exception as ex:  # likely trying to add a dupe node
                            template = "An exception of type {0} occured. Arguments:\n{1!r}"
                            message = template.format(type(ex).__name__, ex.args)
                            # logger().warning(message)
                            continue

    def refresh_unregistered(self):
        """ Updates health of unregistered nodes  """
        logger().info('Refreshing unregistered nodes...')
        for node in net_dao.get_unregistered_nodes():
            if node["host"] + node["port"] != self.host + str(self.port):
                node = Node(node["node_id"], node["node_owner"], node["host"], node["port"], node["phases"])
                if node not in self.connections:
                    self.discover_node(node)

    def connect(self):
        """ determines which nodes to connect to and does so every 5 seconds """
        logger().info('Gathering connections')
        try:
            if self.phases:
                if self.phases & PHASE_1_NODE:
                    self.connect_nodes(PHASE_2_NODE)

                if self.phases & PHASE_2_NODE:
                    self.connect_nodes(PHASE_3_NODE)

                if self.phases & PHASE_3_NODE:
                    self.connect_nodes(PHASE_4_NODE)

                if self.phases & PHASE_4_NODE:
                    self.connect_nodes(PHASE_5_NODE)
        except Exception as ex:
            template = "An exception of type {0} occured. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            logger().warning(message)

    def discover_node(self, node_to_discover):
        """ discover node, get node info from unregistered nodes (updating unregistered nodes) """
        if self.connect_thrift_node(node_to_discover):
            logger().info('successfully connected to unregistered node port: %s', node_to_discover.port)
            try:  # if able to connect to unregistered node
                if self.calc_latency(node_to_discover):
                    net_dao.update_con_activity(node_to_discover)
            finally:  # disconnect node
                logger().info('disconnecting unregistered node port: %s', node_to_discover.port)
                self.disconnect_node(node_to_discover)
        else:  # failed to ping node (not connected)
            net_dao.update_failed_ping(node_to_discover)
            logger().warning('unsuccessful connection attempt to unregistered node port: %s', node_to_discover.port)

    def remove_from_peer_dict(self, node_to_remove):
        """ remove given node in any places it shows up in peer_dict """
        for phase_type in self.peer_dict.keys():
            if node_to_remove.phases & phase_type:
                self.peer_dict[phase_type].remove(node_to_remove)

    def disconnect_node(self, node_to_remove):
        """ disconnects given node and removes from connected structures """
        if node_to_remove is not None:
            try:
                node_to_remove.client.unregister_node(node_to_remove.pass_phrase)
                net_dao.reset_start_time(node_to_remove)
            except Thrift.TException as tx:
                logger().error(('%s' % tx.message))
            try:
                if node_to_remove.transport is not None:
                    node_to_remove.transport.close()
            except Thrift.TException as tx:
                logger().error(('%s' % tx.message))

            if node_to_remove in self.connections:
                self.connections.remove(node_to_remove)
                self.remove_from_peer_dict(node_to_remove)

            node_to_remove.connected = False
            logger().info('%s outbound connection removed', node_to_remove.node_id)

    """
        For now, connect to every node available
        TODO: set upper limit based upon phase
    """
    def connect_nodes(self, phase_type):
        """ attempt to connect each desired node from db """
        nodes = self.load_nodes_by_phase(phase_type)
        for node in nodes:
            self.connect_node(node, phase_type)

    def load_nodes_by_phase(self, phase_type):
        """ return array of nodes to possibly connect to """
        candidates = []
        for node in net_dao.get_by_phase(phase_type):
            if node["host"] is not self.host and node["port"] is not int(self.port):
                node = Node(node["node_id"], "TWDC", node["host"], node["port"], node["phases"])
                self.peer_dict.setdefault(phase_type, [])
                if node not in self.connections:
                    candidates.append(node)
        return candidates

    def connect_node(self, node, phase_type):
        """ add given node to peer_dict and connected list on successful connection """
        if self.connect_thrift_node(node):
            if node not in self.connections:
                net_dao.update_con_start(node)  # updating connection time in db table
                self.peer_dict[phase_type].append(node)
                self.connections.add(node)

    def calc_latency(self, node_to_calc):
        """ calculate latency of given node, remove if node is not connected """
        start = time.clock()
        success = False
        try:
            for i in range(5):
                node_to_calc.client.ping()

            node_to_calc.latency = ((time.clock() - start) / 5) * 1000  # converting to ms
            success = True
        except:  # node not connected
            print(str(sys.exc_info()))
            logger().warning("error attempting to ping an unregistered node: disconnecting node")
            if node_to_calc in self.connections:  # if a registered node disconnects
                self.connections.remove(node_to_calc)
                self.remove_from_peer_dict(node_to_calc)
            try:
                net_dao.update_failed_ping(node_to_calc)
            except Exception as ex:
                template = "An exception of type {0} occured. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                logger().warning(message)

        return success

    def connect_thrift_node(self, node_to_connect):
        """ attempt to connect a node through thrift networking services """
        connection_successful = False
        if not node_to_connect.connected:
            try:
                if node_to_connect not in self.connections:  # and \
                    # peer.connection_attempts < MAX_CONNECTION_ATTEMPTS and \
                    # len(self.peers) < self.max_outbound_connections:
                    logger().info('attempting connect_thrift_node %s:%s', node_to_connect.host, node_to_connect.port)

                    pass_phrase = str(uuid.uuid4())

                    # Make socket
                    transport = TSocket.TSocket(node_to_connect.host, int(node_to_connect.port))

                    # Buffering is critical. Raw sockets are very slow
                    transport = TTransport.TBufferedTransport(transport)

                    # Wrap in a protocol
                    protocol = TBinaryProtocol.TBinaryProtocol(transport)

                    # Create a client to use the protocol encoder
                    client = BlockchainService.Client(protocol)
                    # Connect
                    transport.open()
                    logger().info('about to register')
                    connection_successful = client.register_node(self.this_node, pass_phrase)
                    logger().info('transport open to node %s', node_to_connect.node_id)
                    if connection_successful:
                        node_to_connect.connected = True
                        node_to_connect.pass_phrase = pass_phrase
                        node_to_connect.transport = transport
                        node_to_connect.client = client
                        logger().info('%s accepted outbound connection request.', node_to_connect.node_id)
                        logger().info('node owner: %s', node_to_connect.owner)
                        logger().info('phases provided: %s', '{:05b}'.format(node_to_connect.phases))
                    else:
                        try:
                            net_dao.update_con_attempts(node_to_connect)  # incrementing connection attempts on fail
                        except Exception as ex:
                            template = "An exception of type {0} occured. Arguments:\n{1!r}"
                            message = template.format(type(ex).__name__, ex.args)
                            logger().warning(message)
                        transport.close
                        print(node_to_connect.node_id + ' rejected outbound connection request.')

            except Exception as ex:
                if not connection_successful:
                    net_dao.update_con_attempts(node_to_connect)
                template = "An exception of type {0} occured. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                logger().warning(message)
            finally:
                logger().info('connect_thrift_node %s', str(connection_successful))
        return connection_successful

    def send_block(self, phase_broadcast, block_info, phase):
        """
        send given block info to node with appropriate phase type services (using BlockchainServiceHandler)
        - phase_broadcast (given broadcast function name to use)
        """
        if block_info and phase <= PHASE_5_NODE:
            phase_type = 0b00001 << phase
            phase_broadcast(block_info, phase_type)

    def phase_1_broadcast(self, block_info, phase_type):
        """ sends phase_1 information for phase_2 execution """
        phase_1_msg = self.get_p1_message(block_info)

        for node in self.peer_dict[phase_type]:
            try:
                node.client.phase_1_message(phase_1_msg)
            except:
                logger().warning('failed to submit to node %s', node.node_id)
                continue

    def get_p1_message(self, block_info):
        """ returns thrift phase 1 message structure """
        verification_record = block_info['verification_record']
        transactions = map(convert_to_thrift_transaction, verification_record['verification_info'])
        verification_record = convert_to_thrift_record(verification_record)

        phase_1_msg = message_types.Phase_1_msg()
        phase_1_msg.record = verification_record
        phase_1_msg.transactions = transactions

        return phase_1_msg

    def phase_2_broadcast(self, block_info, phase_type):
        """ sends phase_2 information for phase_3 execution """
        phase_2_msg = self.get_p2_message(block_info)

        for node in self.peer_dict[phase_type]:
            try:
                node.client.phase_2_message(phase_2_msg)
            except:
                logger().warning('failed to submit to node %s', node.node_id)
                continue

    def get_p2_message(self, block_info):
        """returns thrift phase 2 message structure """
        verification_record = block_info['verification_record']
        verification_info = verification_record['verification_info']

        phase_2_msg = message_types.Phase_2_msg()
        phase_2_msg.record = convert_to_thrift_record(verification_record)
        phase_2_msg.valid_txs = map(convert_to_thrift_transaction, verification_info['valid_txs'])
        phase_2_msg.invalid_txs = map(convert_to_thrift_transaction, verification_info['invalid_txs'])
        phase_2_msg.business = verification_info['business']
        phase_2_msg.deploy_location = verification_info['deploy_location']

        return phase_2_msg

    def phase_3_broadcast(self, block_info, phase_type):
        """ send phase_3 information for phase_4 execution """
        phase_3_msg = self.get_p3_message(block_info)

        for node in self.peer_dict[phase_type]:
            try:
                node.client.phase_3_message(phase_3_msg)
            except:
                logger().warning('failed to submit to node %s', node.node_id)
                continue

    def get_p3_message(self, block_info):
        """returns thrift phase 3 message structure """
        verification_record = block_info['verification_record']
        verification_info = verification_record['verification_info']

        phase_3_msg = message_types.Phase_3_msg()
        phase_3_msg.record = convert_to_thrift_record(verification_record)
        phase_3_msg.p2_count = verification_info['p2_count']
        phase_3_msg.businesses = verification_info['businesses']
        phase_3_msg.deploy_locations = verification_info['deploy_locations']
        phase_3_msg.lower_hashes = verification_info['lower_hashes']

        return phase_3_msg

    # TODO: implement this broadcast
    def phase_4_broadcast(self, block_info, phase_type):
        pass

    def public_broadcast(self, block_info, phase):
        """ broadcast to phase 5 nodes for public transmission """
        if block_info and phase <= PHASE_5_NODE:
            # being asked for public broadcast, connect to known phase 5 nodes at this point
            try:
                if self.phases:
                    self.connect_nodes(PHASE_5_NODE)
            except Exception as ex:
                template = "An exception of type {0} occured. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                logger().warning(message)

            phase_msg = None
            verification_record = message_types.VerificationRecord()
            phase_5_msg = message_types.Phase_5_msg()

            if phase == 1:
                phase_msg = self.get_p1_message(block_info)
                verification_record.p1 = phase_msg
            elif phase == 2:
                phase_msg = self.get_p2_message(block_info)
                verification_record.p2 = phase_msg
            elif phase == 3:
                phase_msg = self.get_p3_message(block_info)
                verification_record.p3 = phase_msg
            elif phase == 4:
                pass

            phase_5_msg.verification_record = verification_record

            # send block to all known phase 5 nodes
            if phase_msg:
                for node in self.peer_dict[PHASE_5_NODE]:
                    try:
                        node.client.phase_5_message(phase_5_msg)
                        logger().info('block sent for public transmission...')
                    except:
                        logger().warning('failed to submit to node %s', node.node_id)
                        continue


class BlockchainServiceHandler:
    def __init__(self, connection_manager):
        self.connection_manager = connection_manager
        self.registered_nodes = {}
        self.registered_node_health = {}
        self.incoming_connections = 0

    def setup_tasks(self):
        scheduler = BackgroundScheduler()

        def remove_dead_inbound_connections():
            self.remove_dead_inbound_connections()

        scheduler.add_job(remove_dead_inbound_connections, CronTrigger(second='*/15'))
        scheduler.start()

    def remove_dead_inbound_connections(self):
        pass_phrases = set(self.registered_nodes.keys())
        pass_phrases = pass_phrases.union(set(self.registered_node_health.keys()))
        for pass_phrase in pass_phrases:
            last_heartbeat = self.registered_node_health[pass_phrase]
            if time.time() - last_heartbeat > INBOUND_TIMEOUT:
                self.remove_inbound_connection(pass_phrase)

    def remove_inbound_connection(self, pass_phrase):
        node = None
        if pass_phrase in self.registered_nodes:
            node = self.registered_node_health.pop(pass_phrase)
            del self.registered_nodes[pass_phrase]
            self.incoming_connections -= 1
        return node

    def authorize_pass_phrase(self, pass_phrase):
        if pass_phrase not in self.registered_nodes:
            raise message_types.UnauthorizedException
        # record the last time a message was received from this node
        self.registered_node_health[pass_phrase] = time.time()

    def ping(self):
        return True

    def register_node(self, node_to_register, pass_phrase):
        logger().info('a node is attempting to register')
        connection_authorized = False
        if self.incoming_connections < self.connection_manager.max_inbound_connections:
            # TODO: add more authorization logic here in the future
            self.registered_nodes[pass_phrase] = [node_to_register]
            connection_authorized = True
            self.incoming_connections += 1
            logger().info('accepted inbound connection from %s', node_to_register.node_id)

        return connection_authorized

    def unregister_node(self):
        node = self.remove_inbound_connection()
        logger().info('%s severed inbound connection', node.node_id)

    def get_node_info(self):
        return self.connection_manager.this_node

    def submit_verification(self, block_id, phase, block_record):
        """ submit block record of given block """
        self.connection_manager.processing_node.notify(phase + 1, block_id=block_id, phase=phase, block_record=block_record)

    def phase_1_message(self, phase_1):
        """ submit phase_1 block for phase_2 validation_phase """
        phase_1_info = self.get_phase_1_info(phase_1)
        self.connection_manager.processing_node.notify(2, phase_1_info=phase_1_info)

    def get_phase_1_info(self, phase_1):
        """ return dictionary representation of thrift phase 1 """
        return {
            RECORD: thrift_record_to_dict(phase_1.record),
            VERIFICATION_INFO: map(thrift_transaction_to_dict, phase_1.transactions)
        }

    def phase_2_message(self, phase_2):
        phase_2_info = self.get_phase_2_info(phase_2)
        self.connection_manager.processing_node.notify(3, phase_2_info=phase_2_info)

    def get_phase_2_info(self, phase_2):
        """ return dictionary representation of thrift phase 2 """
        return {
            RECORD: thrift_record_to_dict(phase_2.record),
            VERIFICATION_INFO: {
                'valid_txs': map(thrift_transaction_to_dict, phase_2.valid_txs),
                'invalid_txs': map(thrift_transaction_to_dict, phase_2.invalid_txs),
                'business': phase_2.business,
                'deploy_location': phase_2.deploy_location
            }
        }

    def phase_3_message(self, phase_3):
        phase_3_info = self.get_phase_3_info(phase_3)
        self.connection_manager.processing_node.notify(4, phase_3_info=phase_3_info)

    def get_phase_3_info(self, phase_3):
        """ return dictionary representation of thrift phase 3 """
        return {
            RECORD: thrift_record_to_dict(phase_3.record),
            VERIFICATION_INFO: {
                'lower_hashes': phase_3.lower_hashes,
                'p2_count': phase_3.p2_count,
                'businesses': phase_3.businesses,
                'deploy_locations': phase_3.deploy_locations
            }
        }

    def phase_4_message(self, phase_4):
        # FIXME: sending phase 4 to phase 5 by default, shouldn't be.
        self.connection_manager.processing_node.notify(5, phase_4_info=phase_4)

    def get_phase_4_info(self, phase_4):
        """ return dictionary representation of thrift phase 4 """
        pass

    def phase_5_message(self, phase_5):
        """ determine which phase type being dealt with, convert thrift to dictionary
            and send off for phase 5 (public transmission)
        """
        phase_info = None
        if phase_5.verification_record.p1:
            phase_info = self.get_phase_1_info(phase_5.verification_record.p1)
        elif phase_5.verification_record.p2:
            phase_info = self.get_phase_2_info(phase_5.verification_record.p2)
        elif phase_5.verification_record.p3:
            phase_info = self.get_phase_3_info(phase_5.verification_record.p3)
        elif phase_5.verification_record.p4:
            pass

        self.connection_manager.processing_node.notify(5, phase_5_info=phase_info)

    def get_peers(self):
        """ return list of connections from this node """
        def create_node_from_peer(peer):
            node = message_types.Node()
            node.host = peer.host
            node.port = int(peer.port)
            node.owner = peer.owner
            node.node_id = peer.node_id
            node.phases = peer.phases
            return node

        return map(create_node_from_peer, self.connection_manager.connections)

if __name__ == '__main__':
    net_dao.reset_data()
    connect1 = ConnectionManager('localhost', sys.argv[1], sys.argv[3])

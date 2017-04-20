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
from blockchain.db.postgres import vr_transfers_db
from blockchain.db.postgres import verification_db

from blockchain.db.postgres import sub_to_db
from blockchain.db.postgres import sub_from_db
from blockchain.db.postgres import transaction_db
from blockchain.db.postgres import sub_vr_backlog_db as sub_vr_backlog_db
from blockchain.db.postgres import sub_vr_transfers_db

import gen.messaging.BlockchainService as BlockchainService
import gen.messaging.ttypes as message_types
import db.postgres.postgres as pg

from blockchain.util import thrift_conversions as thrift_converter

from blockchain.util.crypto import validate_subscription

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
VR_DB_LIMIT = 'vr_db_limit'
TXN_DB_LIMIT = 'txn_db_limit'
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
        self.last_transfer_time = 0

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
        self.vr_db_limit = None
        self.txn_db_limit = None
        # phase_type => {nodes} (dictionary of connected nodes)
        self.peer_dict = {}
        self.config = None
        # set of connected nodes
        self.connections = set()
        self.phases = int(phases)
        self.processing_node = processing_node
        # defaults to 15 minutes (900 seconds)
        self.receipt_request_time = 900
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

        if VR_DB_LIMIT in self.config:
            self.vr_db_limit = self.config[VR_DB_LIMIT]

        if TXN_DB_LIMIT in self.config:
            self.txn_db_limit = self.config[TXN_DB_LIMIT]

        # set public_transmission dictionary from yml config
        if self.processing_node:
            self.processing_node.public_transmission = self.config[PUB_TRANS_PROPERTY_KEY]

        self.this_node.host = self.host
        self.this_node.port = int(self.port)
        self.this_node.owner = self.config[OWNER_PROPERTY_KEY]
        self.this_node.node_id = self.config[NODE_ID_PROPERTY_KEY]
        if "receipt_request_time" in self.config:
            self.receipt_request_time = self.config["receipt_request_time"]
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
        """ scheduled tasks that run every x seconds """
        scheduler = BackgroundScheduler()

        scheduler.add_job(self.refresh_registered, CronTrigger(second='*/5'))
        scheduler.add_job(self.refresh_unregistered, CronTrigger(second='*/60'))
        scheduler.add_job(self.connect, CronTrigger(second='*/5'))
        scheduler.add_job(self.subscription_feed, CronTrigger(second='*/5'))

        # the timed_receipt_request only is added to the chron for nodes that are transmitting up the chain.
        if (self.this_node.phases & 0b00111 or
           (self.this_node.phases & 0b01000 and self.config['public_transmission']['p4_pub_trans'])):
            scheduler.add_job(self.timed_receipt_request, CronTrigger(second='*/300'))

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
                            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
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
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            logger().warning(message)

    def discover_node(self, node_to_discover):
        """ discover node, get_verifications node info from unregistered nodes (updating unregistered nodes) """
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
                if node_to_remove in self.peer_dict[phase_type]:
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
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
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
                            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                            message = template.format(type(ex).__name__, ex.args)
                            logger().warning(message)
                        transport.close()
                        print(node_to_connect.node_id + ' rejected outbound connection request.')

            except Exception as ex:
                if not connection_successful:
                    net_dao.update_con_attempts(node_to_connect)
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
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
        phase_1_msg = thrift_converter.get_p1_message(block_info)
        ver_ids = []

        for node in self.peer_dict[phase_type]:
            try:
                ver_ids += node.client.phase_1_message(phase_1_msg)
                vrs = self.get_vrs(node, ver_ids)
                record = message_types.VerificationRecord()
                record.p1 = phase_1_msg
                vrs.append(record)
                self.resolve_data(vrs, 1)
            except Exception as ex:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                logger().warning(message)


    def phase_2_broadcast(self, block_info, phase_type):
        """ sends phase_2 information for phase_3 execution """
        phase_2_msg = thrift_converter.get_p2_message(block_info)
        ver_ids = []

        for node in self.peer_dict[phase_type]:
            try:
                ver_ids += node.client.phase_2_message(phase_2_msg)
                vrs = self.get_vrs(node, ver_ids)
                self.resolve_data(vrs, 2)
            except:
                logger().warning('failed to submit to node %s', node.node_id)
                continue

    def phase_3_broadcast(self, block_info, phase_type):
        """ send phase_3 information for phase_4 execution """
        phase_3_msg = thrift_converter.get_p3_message(block_info)
        ver_ids = []

        for node in self.peer_dict[phase_type]:
            try:
                ver_ids += node.client.phase_3_message(phase_3_msg)
                vrs = self.get_vrs(node, ver_ids)
                self.resolve_data(vrs, 3)
            except:
                logger().warning('failed to submit to node %s', node.node_id)
                continue

    def phase_4_broadcast(self, block_info, phase_type):
        """ send phase_4 information for phase_5 execution """
        ver_ids = []

        verification_record = block_info['verification_record']
        verification_info = verification_record['verification_info']

        phase_4_msg = message_types.Phase_4_msg()
        phase_4_msg.record = thrift_converter.convert_to_thrift_record(verification_record)
        phase_4_msg.lower_hash = verification_info

        for node in self.peer_dict[phase_type]:
            try:
                ver_ids += node.client.phase_4_message(phase_4_msg)
                vrs = self.get_vrs(node, ver_ids)
                self.resolve_data(vrs, 4)
            except:
                logger().warning('failed to submit to node %s', node.node_id)
                continue

    def timed_receipt_request(self):
        """ time based receipt request """
        for node in self.connections:
            if int(time.time()) - node.last_transfer_time >= self.receipt_request_time:
                ver_ids = node.client.receipt_request(node.pass_phrase)
                vrs = self.get_vrs(node, ver_ids)  # verifications matching given verification ids
                self.resolve_data(vrs, node.phases)  # node.phases may present problems since it's in binary

    def subscription_feed(self):
        """ request transactions with associated verification records from subscription """
        subscriptions = sub_to_db.get_all()
        for subscription in subscriptions:
            subscription_node = self.get_subscription_node(subscription)
            if subscription_node:
                # sign subscription
                self.processing_node.get_subscription_signature(subscription)
                subscription_id = subscription['subscription_id']
                # convert to thrift signature for sending to server
                subscription_signature = thrift_converter.convert_to_thrift_signature(subscription['signature'])
                # subscription already approved, request data from server
                if subscription['status'] == "approved":
                    subscription_response = subscription_node.client.subscription_request(subscription_id, subscription_signature)
                    txns = map(thrift_converter.convert_thrift_transaction, subscription_response.transactions)
                    vrs = map(thrift_converter.convert_thrift_verification, subscription_response.verification_records)
                    self.insert_transactions(txns)
                    self.insert_verifications(vrs)
                    if txns or vrs:
                        min_block_id = self.get_min_block_id(vrs)
                        # execute any present subscription smart contracts
                        self.processing_node.sch.execute_ssc(min_block_id, self.vr_db_limit, self.txn_db_limit)
                elif subscription['status'] == "pending":
                    logger().warning("Subscription[sub_id:%s][node_id:%s][node_owner:%s] still in pending status... Waiting for admin(s) approval.",
                                     subscription['subscription_id'], subscription['subscribed_node_id'], subscription['node_owner'])

    def get_subscription_node(self, subscription):
        """ check if client is connected to node subscribed to and return that node. if not, attempt to connect to it and return. """
        if not self.subscription_connected(subscription):
            self.connect_subscription_node(subscription)
        for node in self.connections:
            if subscription["subscribed_node_id"] == node.node_id:
                return node
        return None

    def subscription_connected(self, subscription):
        """ check if connected to subscription node """
        for node in self.connections:
            if subscription["subscribed_node_id"] == node.node_id:
                return True
        return False

    def connect_subscription_node(self, subscription):
        """ connect to subscription node """
        node = net_dao.get(subscription["subscribed_node_id"])
        # check if node is already in database and just not connected
        if node:
            subscription_node = Node(node["node_id"], node["node_owner"], node["host"], node["port"], node["phases"])
            phase = int(node["phases"], 2)
            if phase not in self.peer_dict:
                self.peer_dict.setdefault(phase, [])
            try:
                self.connect_node(subscription_node, phase)
            except:
                logger().warning("Failed to connect to subscription node %s", node['node_id'])
        else:
            # insert new node into table and recursively call connect_subscription_node
            node = Node(subscription['subscribed_node_id'], subscription['node_owner'], subscription['host'], subscription['port'], "00001")
            net_dao.insert_node(node)
            self.connect_subscription_node(subscription)

    def insert_transactions(self, transactions):
        """ insert given transactions into database """
        for txn in transactions:
            try:
                transaction_db.insert_transaction(txn)
            except Exception as ex:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                logger().error(message)
                continue

    def insert_verifications(self, verification_records):
        """ insert given verification records in database """
        for ver in verification_records:
            try:
                verification_db.insert_verification(ver, ver['verification_id'])
            except Exception as ex:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                logger().error(message)
                continue

    def get_min_block_id(self, vrs):
        """ return minimum block id of given verification records """
        return min(v['block_id'] for v in vrs)

    def resolve_data(self, verifications, phase):
        """ store received verifications from node, find replications and store them in transfers table """
        for verification in verifications:
            try:
                verification = thrift_converter.convert_thrift_verification(verification)
                if verification['signature']['signatory'] is not self.this_node.node_id:
                    # run broadcast smart contract (BSC)
                    self.processing_node.sch.execute_bsc(phase, verification)
                    verification_db.insert_verification(verification, verification['verification_id'])
                    # check if there are nodes further down the chain interested in this record
                    replicated_verifications = verification_db.get_all_replication(verification['block_id'], phase, verification['origin_id'])
                    for replicated_ver in replicated_verifications:
                        vr_transfers_db.insert_transfer(replicated_ver['origin_id'], replicated_ver['signature']['signatory'], verification['verification_id'])
                    # check if there are active subscriptions interested in this record
                    self.update_subscription_response(verification)
            except Exception as ex:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                logger().warning(message)

    def get_vrs(self, node, guids):
        """ request unreceived verifications from node, notify node of already received verifications """
        received, unreceived = self.split_items(lambda guid: verification_db.get(guid) is not None, guids)
        verifications = node.client.transfer_data(node.pass_phrase, received, unreceived)
        node.last_transfer_time = int(time.time())

        return verifications

    def update_subscription_response(self, verification_record):
        """ check sub_vr_backlog, check if there are any active subscriptions that have phase criteria
            that match given vr phase. if so, build a response of transactions and matching vrs for this block. """
        server_id = self.this_node.node_id
        block_id = verification_record['block_id']
        backlogs = sub_vr_backlog_db.get_backlogs(block_id)
        # check for backlogged records and insert for transfer
        for bl in backlogs:
            sub_vr_transfers_db.insert_transfer(bl['client_id'], [], [verification_record])
        # subscriptions with phase criteria that meet given record's phase
        subscriptions = sub_from_db.get_by_phase_criteria(verification_record['phase'])
        for sub in subscriptions:
            criteria = sub['criteria']
            # transactions that meet subscription criteria
            transactions = self.get_subscription_txns(criteria, block_id)
            # verification records associated with transactions
            verification_records = []
            for txn in transactions:
                verification_records += self.get_subscription_vrs(txn, server_id)
            # insert new response for subscriber with transactions and vrs
            if transactions or verification_records:
                sub_vr_transfers_db.insert_transfer(sub['subscriber_id'], transactions, verification_records)
            # create backlog for potentially delayed verifications
            sub_vr_backlog_db.insert_backlog(sub['subscriber_id'], block_id)

    def get_subscription_txns(self, criteria, block_id):
        """ retrieve transactions that meet subscription criteria """
        transactions = transaction_db.get_subscription_txns(criteria, block_id)
        return list(transactions)

    def get_subscription_vrs(self, transaction, server_id):
        """ retrieve records for the block matching the given transaction with origin ids matching the server's id. """
        txn_header = transaction["header"]
        verifications_records = []
        if "block_id" in txn_header and txn_header['block_id']:
            verifications_records = verification_db.get_records(block_id=txn_header['block_id'], origin_id=server_id)
        return verifications_records

    @staticmethod
    def split_items(filter_func, items):
        accepted = []
        rejected = []
        for item in items:
            if filter_func(item):
                accepted += [item]
            else:
                rejected += [item]
        return accepted, rejected

    def public_broadcast(self, block_info, phase):
        """ broadcast to phase 5 nodes for public transmission """
        if block_info and phase <= PHASE_5_NODE:
            # being asked for public broadcast, connect to known phase 5 nodes at this point
            try:
                if self.phases:
                    self.connect_nodes(PHASE_5_NODE)
            except Exception as ex:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                logger().warning(message)

            phase_msg = None
            verification_record = message_types.VerificationRecord()
            phase_5_request = message_types.Phase_5_request()

            if phase == 1:
                phase_msg = thrift_converter.get_p1_message(block_info)
                verification_record.p1 = phase_msg
            elif phase == 2:
                phase_msg = thrift_converter.get_p2_message(block_info)
                verification_record.p2 = phase_msg
            elif phase == 3:
                phase_msg = thrift_converter.get_p3_message(block_info)
                verification_record.p3 = phase_msg
            elif phase == 4:
                phase_msg = thrift_converter.get_p4_message(block_info)
                verification_record.p4 = phase_msg

            phase_5_request.verification_record = verification_record

            # send block to all known phase 5 nodes
            if phase_msg:
                for node in self.peer_dict[PHASE_5_NODE]:
                    try:
                        node.client.phase_5_message(phase_5_request)
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
        if pass_phrase:
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
        """ register(store) node connecting to this node """
        logger().info('a node is attempting to register')
        connection_authorized = False
        if pass_phrase and self.incoming_connections < self.connection_manager.max_inbound_connections:
            # TODO: add more authorization logic here in the future
            self.registered_nodes[pass_phrase] = node_to_register
            connection_authorized = True
            self.incoming_connections += 1
            logger().info('accepted inbound connection from %s', node_to_register.node_id)

        return connection_authorized

    def unregister_node(self, pass_phrase):
        if pass_phrase:
            node = self.remove_inbound_connection(pass_phrase)
            logger().info('%s severed inbound connection', node.node_id)

    def get_node_info(self):
        return self.connection_manager.this_node

    def submit_verification(self, block_id, phase, block_record):
        """ submit block record of given block """
        self.connection_manager.processing_node.notify(phase + 1, block_id=block_id, phase=phase, block_record=block_record)

    def phase_1_message(self, phase_1):
        """ submit phase_1 block for phase_2 validation_phase """
        phase_1_info = thrift_converter.get_phase_1_info(phase_1)
        self.connection_manager.processing_node.notify(2, phase_1_info=phase_1_info)
        return self.get_unsent_transfer_ids(transfer_to=phase_1_info[RECORD]['signature']['signatory'])

    def phase_2_message(self, phase_2):
        phase_2_info = thrift_converter.get_phase_2_info(phase_2)
        self.connection_manager.processing_node.notify(3, phase_2_info=phase_2_info)
        return self.get_unsent_transfer_ids(transfer_to=phase_2_info[RECORD]['signature']['signatory'])

    def phase_3_message(self, phase_3):
        phase_3_info = thrift_converter.get_phase_3_info(phase_3)
        self.connection_manager.processing_node.notify(4, phase_3_info=phase_3_info)
        return self.get_unsent_transfer_ids(transfer_to=phase_3_info[RECORD]['signature']['signatory'])

    def phase_4_message(self, phase_4):
        phase_4_info = thrift_converter.get_phase_4_info(phase_4)
        return self.get_unsent_transfer_ids(transfer_to=phase_4_info[RECORD]['signature']['signatory'])

    def phase_5_message(self, phase_5):
        """ determine which phase type being dealt with, convert thrift to dictionary
            and send off for phase 5 (public transmission)
        """
        phase_info = None
        if phase_5.verification_record.p1:
            phase_info = thrift_converter.get_phase_1_info(phase_5.verification_record.p1)
        elif phase_5.verification_record.p2:
            phase_info = thrift_converter.get_phase_2_info(phase_5.verification_record.p2)
        elif phase_5.verification_record.p3:
            phase_info = thrift_converter.get_phase_3_info(phase_5.verification_record.p3)
        elif phase_5.verification_record.p4:
            phase_info = thrift_converter.get_phase_4_info(phase_5.verification_record.p4)

        self.connection_manager.processing_node.notify(5, verification=phase_info)

        return []

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

    def transfer_data(self, pass_phrase, received, unreceived):
        """ mark verifications as sent and return unsent verifications """
        if pass_phrase:
            self.authorize_pass_phrase(pass_phrase)
            transfer_node = self.registered_nodes[pass_phrase]
            verifications = []
            guids = received + unreceived

            # mark all verifications received as sent
            for guid in guids:
                vr_transfers_db.set_verification_sent(transfer_node.node_id, guid)

            # retrieve unreceived records
            for guid in unreceived:
                verifications.append(verification_db.get(guid))

            # format verifications to list of thrift structs for returning
            thrift_verifications = map(thrift_converter.get_verification_type, verifications)

            return thrift_verifications

    def receipt_request(self, pass_phrase):
        """ return unsent transfer ids to calling node """
        if pass_phrase:
            self.authorize_pass_phrase(pass_phrase)
            transfer_node = self.registered_nodes[pass_phrase]
            return self.get_unsent_transfer_ids(transfer_node.node_id)

    def subscription_provisioning(self, subscription_id, criteria, phase_criteria, create_ts, public_key):
        """ initial communication between subscription """
        try:
            sub_from_db.insert_subscription(subscription_id, criteria, phase_criteria, public_key, create_ts)
        except:
            logger().warning("A subscription SQL error has occurred.")
        pass

    def subscription_request(self, subscription_id, subscription_signature):
        """ return transactions and associated verification records that meet criteria made by client """
        transactions = []
        verification_records = []
        subscriber_info = sub_from_db.get(subscription_id)
        # convert thrift signature to dictionary
        subscriber_signature = thrift_converter.convert_thrift_signature(subscription_signature)
        criteria = subscriber_info['criteria']
        public_key = subscriber_signature["public_key"]
        # validate subscription signature
        if validate_subscription(subscriber_signature, criteria, subscriber_info['create_ts'], public_key):
            # query transactions/vrs ready to send to calling subscription node
            try:
                subscription_messages = list(sub_vr_transfers_db.get_all(subscriber_info['subscriber_id']))
                for message in subscription_messages:
                    transactions += map(thrift_converter.convert_to_thrift_transaction, message['transactions'])
                    verification_records += map(thrift_converter.get_verification_type, message['verifications'])

                # convert to thrift friendly response
                subscription_response = message_types.SubscriptionResponse()
                subscription_response.transactions = transactions
                subscription_response.verification_records = verification_records
                return subscription_response
            except Exception as ex:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                logger().warning(message)

    def get_unsent_transfer_ids(self, transfer_to):
        """ retrieve unsent transfer record info (data used for querying block_verification database) """
        unsent_transfer_ids = []
        try:
            logger().info("Retrieving unsent transfer ids...")
            for transfer_record in vr_transfers_db.get_unsent_verification_records(transfer_to):
                unsent_transfer_ids.append(transfer_record['verification_id'])
        except:
            logger().warning("An SQL error has occurred.")

        return unsent_transfer_ids

if __name__ == '__main__':
    net_dao.reset_data()
    connect1 = ConnectionManager('localhost', sys.argv[1], sys.argv[3])

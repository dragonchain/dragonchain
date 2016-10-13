"""
Service task to handle connection management & RMI
"""
import sys

sys.path.append('gen')

from yaml import load

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import messaging.BlockchainService as BlockchainService
import messaging.ttypes as message_types
from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer
import logging
import time
import uuid

DEFAULT_PORT = 9080
MAX_CONNECTION_ATTEMPTS = 5
NODE_ID_PROPERTY_KEY = 'node_id'
OWNER_PROPERTY_KEY = 'owner'
INBOUND_TIMEOUT = 30  # seconds


def logger(name="network-manager"):
    return logging.getLogger(name)


class Node(object):
    def __init__(self, node_id, node_owner, host, port):
        self.node_id = node_id
        self.owner = node_owner
        self.host = host
        self.port = port
        self.peers = []
        self.latency = 0
        self.client = None
        self.transport = None
        self.connection_attempts = 0
        self.pass_phrase = None

    def __eq__(self, other):
        return hash(self.node_id) == hash(other.node_id)

    def __hash__(self):
        return hash(self.node_id)


class ConnectionManager(object):
    def __init__(self, host, port, max_inbound_connections=50, max_outbound_connections=50):
        self.host = host
        self.port = port
        self.peers = []
        self.config = None
        self.connections = []
        self.required_nodes = []
        """ Load configured nodelist """
        self.load_config()
        print('loaded network config')
        self.load_required_nodes()
        self.candidates = self.required_nodes
        print('configured required nodes')
        self.schedule_tasks()
        print('scheduled network tasks')
        self.max_inbound_connections = max_inbound_connections
        self.max_outbound_connections = max_outbound_connections
        #BLOCKING
        self.start_service_handler()
        print('RMI service handler started')

    def load_config(self):
        if self.config is None:
            self.config = load(file('../blockchain.yml'))
        self.this_node = message_types.Node()
        self.this_node.host = self.host
        self.this_node.port = int(self.port)
        self.this_node.owner = self.config[OWNER_PROPERTY_KEY]
        self.this_node.node_id = self.config[NODE_ID_PROPERTY_KEY]

    def start_service_handler(self):

        handler = BlockchainServiceHandler(self)
        processor = BlockchainService.Processor(handler)
        transport = TSocket.TServerSocket(port=self.port)
        tfactory = TTransport.TBufferedTransportFactory()
        pfactory = TBinaryProtocol.TBinaryProtocolFactory()
        server = TServer.TThreadedServer(processor, transport, tfactory, pfactory)
        print('starting server...')
        server.serve()
        print('server started')

    def load_required_nodes(self):
        print(self.host)
        print(self.port)
        for peer in self.config['peers']:
            socket = peer.split(':')
            if len(socket) > 0:
                host = socket[0]
            else:
                # empty host, nothing to do
                continue

            if len(socket) > 1:
                port = socket[1]
            else:
                port = DEFAULT_PORT
            if peer != self.host + ':' + self.port:
                node = Node(None, None, host, port)
                self.required_nodes.append(node)
                print('configured required node ' + peer)

    def schedule_tasks(self):
        scheduler = BackgroundScheduler()

        def refresh_connections():
            self.refresh_connections()

        def find_peers():
            self.find_peers()

        def update_candidates():
            self.update_candidates()

        def select_connections():
            self.select_connections()

        scheduler.add_job(refresh_connections, CronTrigger(second='*/5'))
        scheduler.add_job(find_peers, CronTrigger(second='*/5'))
        scheduler.add_job(update_candidates, CronTrigger(second='*/5'))
        scheduler.add_job(select_connections, CronTrigger(second='*/5'))
        scheduler.start()

    def add_candidate(self, node):
        normalized_node = Node(node.node_id, node.owner, node.host, node.port)
        self.candidates.append(normalized_node)
        print('candidate node added (' + node.node_id + ')')

    def add_peer(self, peer):
        connection_successful = False
        try:
            if peer not in self.peers:  #and \
                #peer.connection_attempts < MAX_CONNECTION_ATTEMPTS and \
                #len(self.peers) < self.max_outbound_connections:
                print('add_peer ' + peer.host + ':' + peer.port)
                self.peers.append(peer)

                pass_phrase = str(uuid.uuid4())

                # Make socket
                transport = TSocket.TSocket(peer.host, peer.port)

                # Buffering is critical. Raw sockets are very slow
                transport = TTransport.TBufferedTransport(transport)

                # Wrap in a protocol
                protocol = TBinaryProtocol.TBinaryProtocol(transport)

                # Create a client to use the protocol encoder
                client = BlockchainService.Client(protocol)
                # Connect!
                transport.open()
                print('about to register')
                connection_successful = client.register_node(self.this_node, pass_phrase)
                print('transport open to peer ' + str(peer))
                if connection_successful:
                    peer.pass_phrase = pass_phrase
                    # Store if successful
                    peer.transport = transport
                    peer.client = client
                    print(peer.node_id + ' accepted outbound connection request.')
                else:
                    transport.close
                    print(peer.node_id + ' rejected outbound connection request.')

        except:
            e = sys.exc_info()[0]
            self.peers.remove(peer)
            peer.connection_attempts += 1
            print(e.args)
        finally:
            print('add_peer ' + connection_successful)
        return connection_successful

    def remove_peer(self, peer_to_remove):
        found_peer = None
        for peer in self.peers:
            if peer.node_id == peer_to_remove.node_id:
                found_peer = peer
                break

        if found_peer is not None:
            try:
                found_peer.client.unregister_node(found_peer.pass_phrase)
            except Thrift.TException as tx:
                logger().error(('%s' % tx.message))
            try:
                if found_peer.transport is not None:
                    found_peer.transport.close()
            except Thrift.TException as tx:
                logger().error(('%s' % tx.message))

            self.peers.remove(found_peer)
            print(found_peer.node_id + ' outbound connection removed')

    def refresh_connections(self):
        print('connection refresh')
        for peer in self.peers:
            #Fill in any missing peer info
            if peer.node_id is None or peer.owner is None:
                info = peer.client.get_node_info()
                peer.node_id = info.node_id
                peer.owner = info.owner
            #Update latency
            start = time.clock()
            for i in range(5):
                peer.client.ping()

            peer.latency = (time.clock() - start) / 5

    def find_peers(self):
        print('peer discovery')
        """ find_peers updates the list of peers for each candidate and connected node """
        for peer in self.peers:
            peer.peers = peer.client.get_peers()

    def update_candidates(self):
        """
         Flatten the list of peer's peers into candidates
        """
        for peer in self.peers:
            filtered_peers = filter(lambda p: p not in self.candidates and p not in self.peers, peer.peers)
            self.candidates = self.candidates.__add__(filtered_peers)
        print('updated candidate list')

    def select_connections(self):
        print('select connections ' + str(self.candidates))
        """
        For now, connect to every node available
        """
        self.candidates = filter(lambda node: not self.add_peer(node), self.candidates)


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
        #record the last time a message was received from this node
        self.registered_node_health[pass_phrase] = time.time()

    def ping(self):
        return True

    def register_node(self, node, pass_phrase):
        print('a node is attempting to register')
        connection_authorized = False
        if self.incoming_connections < self.connection_manager.max_inbound_connections:
            # TODO: add more authorization logic here in the future
            self.registered_nodes[pass_phrase] = [node]
            connection_authorized = True
            # Add incoming connection as a candidate node
            self.connection_manager.add_candidate(node)
            self.incoming_connections += 1
            print('accepted inbound connection from ' + node.node_id)

        return connection_authorized

    def unregister_node(self):
        node = self.remove_inbound_connection()
        print(node.node_id + ' severed inbound connection')

    def get_node_info(self, pass_phrase):
        self.authorize_pass_phrase(pass_phrase)
        return self.connection_manager.this_node

    def submit_verifications(self, verifications, origins):
        #self.authorize_pass_phrase(pass_phrase)
        print ('verifications received ' + str(verifications))

    def submit_transactions(self, transactions, origins):
        #self.authorize_pass_phrase(pass_phrase)
        print ('transactions submitted ' + str(transactions))

    def get_peers(self):
        #self.authorize_pass_phrase(pass_phrase)

        def create_node_from_peer(peer):
            node = message_types.Node()
            node.host = peer.host
            node.port = peer.port
            node.owner = peer.owner
            node.node_id = peer.node_id
            return node

        return map(create_node_from_peer, self.connection_manager.peers)
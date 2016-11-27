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

from blockchain.block import Block, \
    BLOCK_FIXATE_OFFSET, \
    BLOCK_INTERVAL, \
    get_block_time, \
    get_current_block_id

from blockchain.util.crypto import valid_transaction_sig, sign_verification_record, validate_verification_record, deep_hash

from db.postgres import transaction_db
from db.postgres import verfication_db
from db.postgres import postgres

import network

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import logging
import argparse
import time

# TODO increase these for network sizing and later deliver via blockchain
P2_COUNT_REQ = 1
P2_BUS_COUNT_REQ = 1
P2_LOC_COUNT_REQ = 1

BLOCK_ID = 'block_id'
ORIGIN_ID = 'origin_id'

PHASE = 'phase'

SIGNATURE = 'signature'
HASH = 'hash'


def logger(name="verifier-service"):
    return logging.getLogger(name)


class ProcessingNode(object):
    PHASE_1_NAME = 'approval_phase'
    PHASE_2_NAME = 'validation_phase'
    PHASE_3_NAME = 'notary_phase'
    PHASE_4_NAME = 'internal_audit_phase'
    PHASE_5_NAME = 'external_audit_phase'

    def __init__(self, phase_config, service_config):
        self.phase_config = phase_config
        self.service_config = service_config
        self._scheduler = BackgroundScheduler()
        self._config_handlers = {
            PHASE: self._phase_type_config_handler,
            'cron': self._cron_type_config_handler,
            'observer': self._observer_type_config_handler
        }
        self._registrations = {}
        self._configured_phases = []
        self._register_configs()

        # dictionary of public transmission flags. set by network, obtained through yml config file.
        self.public_transmission = None

        phase = self.phase_config[0][PHASE]
        self.network = network.ConnectionManager(self.service_config['host'], self.service_config['port'], 0b00001 << phase - 1, self)

    def start(self):
        """ Start the NON-blocking scheduler """

        # TODO: if network not available, we will need a daemon running to rebroadcast records that haven't moved forward
        self._scheduler.start()
        self._init_networking()

    def notify(self, event_name, **kwargs):
        """ Trigger phases and any added observables """
        observers = self._registrations[event_name]
        for observer in observers:
            observer["callback"](config=observer["config"], **kwargs)

    """ INTERNAL METHODS """

    def _init_networking(self):
        """ currently only starts up network, may add more features """
        print 'initializing network'
        self.network.start_service_handler()

    def _register_configs(self):
        for config in self.phase_config:
            self._config_handlers[config["type"]](config)

    def _add_registration(self, event_name, callback, config):
        if event_name not in self._registrations:
            self._registrations[event_name] = []
        self._registrations[event_name] += [{
            'callback': callback,
            'config': config
        }]

    def _phase_type_config_handler(self, config):
        # Prevent duplicate registration of the same phase index
        if config[PHASE] not in self._configured_phases:
            self._configured_phases += [config[PHASE]]
        else:
            raise Exception("Phase " + config[PHASE] + " has already been registered.")

        if config[PHASE] == 1:
            # Register the primary phase observer
            self._add_registration(1, self._execute_phase_1, config)

            # Setup phase 1 cron
            trigger = CronTrigger(second='*/5')

            # setup the scheduler task
            def trigger_handler():
                self.notify(event_name=1, current_block_id=get_current_block_id())

            # schedule task using cron trigger
            self._scheduler.add_job(trigger_handler, trigger)
            logger().info("Phase 1 configured")
        elif config[PHASE] == 2:
            self._add_registration(2, self._execute_phase_2, config)

        elif config[PHASE] == 3:
            self._add_registration(3, self._execute_phase_3, config)

        elif config[PHASE] == 4:
            self._add_registration(4, self._execute_phase_4, config)

        elif config[PHASE] == 5:
            self._add_registration(5, self._execute_phase_5, config)

    def _cron_type_config_handler(self, config):
        """
        Cron callbacks are called with the processing node instance and config dict as params
        e.g. callback(ProcessingNode, config)
        """
        if 'cron_params' not in config:
            raise Exception("The cron observer config is missing cron_params.")
        if 'callback' not in config:
            raise Exception("The cron job is missing a 'callback' task")

        trigger = CronTrigger(**config['cron_params'])

        def trigger_handler():
            config['callback'](self, config)

        # schedule task using cron trigger
        self._scheduler.add_job(trigger_handler, trigger)

    def _observer_type_config_handler(self, config):
        if 'event_name' not in config:
            raise Exception("Observer config must have an event_name specified")
        if 'callback' not in config:
            raise Exception("Observer config must provide a callback function")

        self._add_registration(config['event_name'], config['callback'], config)

    def strip_payload(self, transactions):
        """ remove payloads from given transactions (phases beyond phase_1 shouldn't need it) """
        for transaction in transactions:
            try:
                transaction['payload'] = None
            except:
                logger().warning('failed to remove payload from transaction %s: transaction may not contain payload', transaction.id)
                continue

    def get_prior_hash(self, origin_id, phase):
        """
        returns prior block hash of curr_block_id.
        returns None if no block_id was found -- meaning this is the first block.

        Args:
            origin_id:
        """
        prior_hash = None
        if phase:
            prior_block = verfication_db.get_prior_block(origin_id, phase)

            if prior_block:
                prior_hash = prior_block[SIGNATURE][HASH]

        return prior_hash

    def _execute_phase_1(self, config, current_block_id):
        """
        TODO update all EXEC comments/docs
        * Each node gathers all transactions that may be included in the prospective block and groups them by transaction owner.
        * All transactions owned (or sourced from) a respective node's business unit or system (owned) are grouped for approval.
        * All transactions not owned by the node's business unit or system (others) are grouped for validation.
        * All owned transactions are verified per business rules, configurable, (e.g, existence or non-existence of particular fields, with field value validation logic).
        * All owned and verified transactions are "approved" by executing the Transaction Verification Signing Process defined below.
        * Any transactions deemed "unapproved" will be taken out of the prospective block from a node's perspective by non-inclusion in the signing process, and sent to a system "pool" or "queue" for analysis and alternate processing
        * All other (non-owned) transactions are validated to system wide rules agreed upon for all nodes through business and system processes.
        * All other (non-owned) transactions are declared "valid" by the node by executing the Transaction Verification Signing Process defined below.
        * Any transactions deemed "invalid" will be taken out of the prospective block from a node's perspective by non-inclusion in the signing process, and sent to a system "pool" or "queue" for analysis and alternate processing.
        """
        print("Phase 1 Verify Start.")
        # Group transactions for last 5 seconds into current block id
        block_bound_lower_ts = get_block_time(current_block_id - BLOCK_FIXATE_OFFSET)
        print ("""Time bounds: %i - %i""" % (block_bound_lower_ts, block_bound_lower_ts + BLOCK_INTERVAL))
        transaction_db.fixate_block(block_bound_lower_ts, block_bound_lower_ts + BLOCK_INTERVAL, current_block_id)

        if 'approve_block' in config:
            return config['approve_block'](config, current_block_id)

        transactions = transaction_db.get_all(block_id=current_block_id)

        # Validate the schema and structure of the transactions
        valid_transactions, invalid_transactions = self.split_items(valid_transaction_sig, transactions)

        # Use the custom approval code if configured, otherwise approve all valid transaction
        rejected_transactions = []
        if 'approve_transaction' in config:
            approved_transactions, rejected_transactions = \
                self.split_items(config['approve_transaction'], valid_transactions)
        else:
            approved_transactions = valid_transactions

        if len(approved_transactions) > 0:
            # update status of approved transactions
            for tx in approved_transactions:
                tx["header"]["status"] = "approved"
                transaction_db.update_transaction(tx)

            # stripping payload from all transactions before signing
            self.strip_payload(approved_transactions)

            phase = 1
            # signatory equals origin_id in phase 1
            signatory = origin_id = self.network.this_node.node_id
            prior_block_hash = self.get_prior_hash(origin_id, phase)
            verification_info = approved_transactions

            lower_hash = str(deep_hash(0))

            # sign approved transactions
            block_info = sign_verification_record(signatory,
                                                  prior_block_hash,
                                                  lower_hash,
                                                  self.service_config['public_key'],
                                                  self.service_config['private_key'],
                                                  current_block_id,
                                                  phase,
                                                  origin_id,
                                                  int(time.time()),
                                                  self.public_transmission,
                                                  verification_info)

            # store signed phase specific data
            verfication_db.insert_verification(block_info['verification_record'])

            # send block info off for public transmission if configured to do so
            if block_info['verification_record']['public_transmission']['p1_pub_trans']:
                self.network.public_broadcast(block_info, phase)

            # send block info for phase 2 validation
            self.network.send_block(self.network.phase_1_broadcast, block_info, phase)
            print("Phase 1 signed " + str(len(approved_transactions)) + " transactions")

        # update status transactions that were rejected
        if len(rejected_transactions) > 0:
            for tx in rejected_transactions:
                tx["header"]["status"] = "rejected"
                transaction_db.update_transaction(tx)

    def _execute_phase_2(self, config, phase_1_info):
        """
        * At this point, any participating processing nodes will have appended signed "approvals" of their respectively owned transactions and signed "validations" of un-owned transactions (see Phase 1 Verification Process).
        * Processing nodes participating in Phase 2 Verification may be a different set of nodes than the set of nodes participating in Phase 1 Verification.
        * Processing nodes may be defined for the sole purpose of Phase 2 verification (without any "owned" transactions in the system).
        * A node participating in Phase 2 verification will verify that all transactions in the prospective block are "approved" by their respective owners and are not declared invalid by a system configured portion (e.g. percentage, plurality, or majority).
        * Any transactions which are not approved will be taken out of the prospective block and "bumped" to the next block now - (d * T) for Phase 1 processing.
        * If a non-approved transaction which is older than a system configured time for the transaction type and owner, the transaction will not be "bumped" to the next block, but instead be placed in a system "pool" or "queue" for later handling or alternate processing.
        * All signed "approval" verification units will be grouped, concatenated, and cryptographically signed.
        * A "Phase 2 signature structure" is created and appended to the block.
        """

        """
        - check block sig
        - req: tx_type, tx_id, tx_ts, owner (origin - original phase_1 node_id), trans_sig
          - tx minus the payload
        """
        phase = 2
        phase_1_record = phase_1_info["record"]
        p1_verification_info = phase_1_info["verification_info"]
        phase_1_record['verification_info'] = p1_verification_info
        prior_block_hash = self.get_prior_hash(phase_1_record[ORIGIN_ID], phase)

        # validate phase_1's verification record
        if validate_verification_record(phase_1_record, p1_verification_info):
            # storing valid verification record
            verfication_db.insert_verification(phase_1_record)

            # updating record phase
            phase_1_record[PHASE] = phase

            valid_transactions, invalid_transactions = self.check_tx_requirements(p1_verification_info)

            verification_info = {
                'valid_txs': valid_transactions,
                'invalid_txs': invalid_transactions,
                'business': self.network.business,
                'deploy_location': self.network.deploy_location
            }

            lower_hash = phase_1_record[SIGNATURE][HASH]

            # sign verification and rewrite record
            block_info = sign_verification_record(self.network.this_node.node_id,
                                                  prior_block_hash,
                                                  lower_hash,
                                                  self.service_config['public_key'],
                                                  self.service_config['private_key'],
                                                  phase_1_record[BLOCK_ID],
                                                  phase_1_record[PHASE],
                                                  phase_1_record[ORIGIN_ID],
                                                  int(time.time()),
                                                  phase_1_record['public_transmission'],
                                                  verification_info
                                                  )

            # inserting verification info after signing
            verfication_db.insert_verification(block_info['verification_record'])

            # send block info off for public transmission if configured to do so
            if phase_1_record['public_transmission']['p2_pub_trans']:
                self.network.public_broadcast(block_info, phase)

            # send block info for phase 3 validation
                self.network.send_block(self.network.phase_2_broadcast, block_info, phase_1_record[PHASE])

            print "phase_2 executed"

    def check_tx_requirements(self, transactions):
        """ check if given transactions contain required fields """
        valid = True
        valid_txs, invalid_txs = [], []
        for tx in transactions:
            tx_header = tx['header']
            if not tx_header['transaction_type']:
                valid = False
            elif not tx_header['transaction_id']:
                valid = False
            elif not tx_header['transaction_ts']:
                valid = False
            elif not tx_header['owner']:
                valid = False
            elif not self.check_tx_sig_existence(tx):
                valid = False
            elif not valid_transaction_sig(tx):
                valid = False

            if valid:
                valid_txs.append(tx)
            else:
                invalid_txs.append(tx)
                valid = True

        return valid_txs, invalid_txs

    def check_tx_sig_existence(self, transaction):
        """ checks signature of given transaction """
        signature = transaction[SIGNATURE]
        valid = True
        if not signature:
            valid = False
        elif not signature[SIGNATURE]:
            valid = False
        elif not signature[HASH]:
            valid = False

        return valid

    def _execute_phase_3(self, config, phase_2_info):
        """
        * At this point, any participating processing nodes will have appended signed Phase 2 verification proof to the block.
        * Processing nodes participating in Phase 3 Verification may be a different set of nodes than the set of nodes participating in Phase 1 and Phase 2 Verification processes.
        * Processing nodes may be defined for the sole purpose of Phase 3 verification (e.g. for independent blockchain verification auditing purposes).
        * A participating node will verify that no invalid transaction has been included in the set of approved transaction.
        * A participating node will verify that all "approved" transactions are signed by their respective owner.
        * A node may perform extra validation steps on all transactions and verification units.
        * All signed "Phase 3 Signature Structures" will be grouped, concatenated, and cryptographically signed by the node.
        """
        phase = 3
        phase_2_record = phase_2_info['record']
        p2_verification_info = phase_2_info['verification_info']
        phase_2_record['verification_info'] = p2_verification_info
        prior_block_hash = self.get_prior_hash(phase_2_record[ORIGIN_ID], phase)

        # validate phase_2's verification record
        if validate_verification_record(phase_2_record, p2_verification_info):
            # storing valid verification record
            verfication_db.insert_verification(phase_2_record)

            phase_2_records = self.get_sig_records(phase_2_record)

            signatories, businesses, locations = self.get_verification_diversity(phase_2_records)

            # checking if passed requirements to move on to next phase
            if len(signatories) >= P2_COUNT_REQ and len(businesses) >= P2_BUS_COUNT_REQ and len(locations) >= P2_LOC_COUNT_REQ:
                # updating record phase
                phase_2_record[PHASE] = phase
                lower_hashes = [record[SIGNATURE]['signatory'] + ":" + record[SIGNATURE][HASH]
                                      for record in phase_2_records]

                verification_info = {
                    'lower_hashes': lower_hashes,
                    'p2_count': len(signatories),
                    'businesses': list(businesses),
                    'deploy_locations': list(locations)
                }

                lower_hash = str(deep_hash(lower_hashes))

                # sign verification and rewrite record
                block_info = sign_verification_record(self.network.this_node.node_id,
                                                      prior_block_hash,
                                                      lower_hash,
                                                      self.service_config['public_key'],
                                                      self.service_config['private_key'],
                                                      phase_2_record[BLOCK_ID],
                                                      phase_2_record[PHASE],
                                                      phase_2_record[ORIGIN_ID],
                                                      int(time.time()),
                                                      phase_2_record['public_transmission'],
                                                      verification_info
                                                      )

                # inserting verification info after signing
                verfication_db.insert_verification(block_info['verification_record'])

                # send block info off for public transmission if configured to do so
                if phase_2_record['public_transmission']['p3_pub_trans']:
                    self.network.public_broadcast(block_info, phase)

                # send block info for phase 4 validation
                self.network.send_block(self.network.phase_3_broadcast, block_info, phase)
                print "phase 3 executed"

    def get_sig_records(self, verification_record):
        """
        check how many phase signings have been received for given block
        search criteria -- origin_id, block_id, phase
        """
        block_id = verification_record[BLOCK_ID]
        origin_id = verification_record[ORIGIN_ID]
        phase = verification_record[PHASE]

        # get number of phase validations received
        records = verfication_db.get_records(block_id, origin_id, phase)

        return records

    def get_verification_diversity(self, records):
        """
        retrieve number of signing records found (not allowing dupes)
        called by phase 3 to check count requirements before sending block
        returns number of unique signatories, businesses and deploy locations
        """
        signatories = set()
        business_count = set()
        location_count = set()

        for record in records:
            signatory = record[SIGNATURE]['signatory']
            business = record['verification_info']['business']
            deploy_location = record['verification_info']['deploy_location']

            if signatory:
                signatories.add(signatory)
            if business:
                business_count.add(business)
            if deploy_location:
                location_count.add(deploy_location)

        return signatories, business_count, location_count

    def _execute_phase_4(self, config, phase_3_info):
        """ external partner notary phase """
        phase = 4
        phase_3_record = phase_3_info['record']
        p3_verification_info = phase_3_info['verification_info']
        phase_3_record['verification_info'] = p3_verification_info
        prior_block_hash = self.get_prior_hash(phase_3_record[ORIGIN_ID], phase)

        # validate phase_3's verification record
        if validate_verification_record(phase_3_record, p3_verification_info):
            # storing valid verification record
            verfication_db.insert_verification(phase_3_record)

            # updating record phase
            phase_3_record[PHASE] = phase

            lower_hash = phase_3_record[SIGNATURE][HASH]

            # sign verification and rewrite record
            block_info = sign_verification_record(self.network.this_node.node_id,
                                                  prior_block_hash,
                                                  lower_hash,
                                                  self.service_config['public_key'],
                                                  self.service_config['private_key'],
                                                  phase_3_record[BLOCK_ID],
                                                  phase_3_record[PHASE],
                                                  phase_3_record[ORIGIN_ID],
                                                  int(time.time()),
                                                  phase_3_record['public_transmission'],
                                                  None
                                                  )

            # inserting verification info after signing
            verfication_db.insert_verification(block_info['verification_record'])

            # send block info off for public transmission if configured to do so
            if phase_3_record['public_transmission']['p4_pub_trans']:
                self.network.public_broadcast(block_info, phase)

            # self.network.send_block(self.network.phase_4_broadcast, block_info, phase)
            print "phase 4 executed"

    def _execute_phase_5(self, config, phase_5_info):
        """ public, Bitcoin bridge phase """
        print "phase 5 executed"

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


def main():
    try:
        logger().info("Setting up argparse")
        parser = argparse.ArgumentParser(description='Process some integers.')
        parser.add_argument('--phase', type=int)
        parser.add_argument('--host', default="localhost")
        parser.add_argument('-p', '--port', type=int, default=8080)
        parser.add_argument('--debug', default=True, action="store_true")
        parser.add_argument('--private-key', dest="private_key", required=True, help="ECDSA private key for signing")
        parser.add_argument('--public-key', dest="public_key", required=True, help="ECDSA public key for signing")

        logger().info("Parsing arguments")
        args = vars(parser.parse_args())

        private_key = args["private_key"]

        with open(private_key, 'r') as key:
            private_key = key.read()

        public_key = args["public_key"]

        with open(public_key, 'r') as key:
            public_key = key.read()

        host = args["host"]
        port = args["port"]
        phase = args[PHASE]

        ProcessingNode([{
            "type": PHASE,
            PHASE: phase
        }], {
            "private_key": private_key,
            "public_key": public_key,
            "owner": "DTSS",
            "host": host,
            "port": port
        }).start()

    finally:
        postgres.cleanup()


# start calling f now and every 60 sec thereafter

if __name__ == '__main__':
    main()

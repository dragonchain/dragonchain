__author__ = 'j03'

from blockchain.block import Block,               \
                             BLOCK_FIXATE_OFFSET, \
                             BLOCK_INTERVAL,      \
                             get_block_time,      \
                             get_current_block_id

from blockchain.txn import validate_transaction, sign_signatures, hash_list
from db.postgres import transaction_db
from db.postgres import verfication_db
from db.postgres import postgres
import network

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import logging
import argparse
import time


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
        #internal use only
        self._scheduler = BlockingScheduler()
        self._config_handlers = {
            'phase': self._phase_type_config_handler,
            'cron': self._cron_type_config_handler,
            'observer': self._observer_type_config_handler
        }
        self._registrations = {}
        self._configured_phases = []
        self._init_networking()
        self._register_configs()

    def start(self):
        #Start the blocking scheduler
        self._scheduler.start()

    #Trigger phases and any added observables
    def notify(self, event_name, **kwargs):
        observers = self._registrations[event_name]
        for observer in observers:
            observer["callback"](config=observer["config"], **kwargs)

    def sign_transactions(self, phase, approved_transactions, rejected_transactions=None):
        """Sign the passed set of transactions and return the sig JSON"""
        signature, transaction_hash =\
            sign_signatures(map(lambda tx: tx["signature"], approved_transactions), self.service_config.private_key)
        block_id = None
        #Get the current block id
        if len(approved_transactions) > 0:
            block_id = approved_transactions[0]["header"]["block_id"]
        elif rejected_transactions and len(rejected_transactions) > 0:
            block_id = rejected_transactions[0]["header"]["block_id"]

        block_verification = {
            "verified_ts": int(time.time()),
            "block_id": block_id,
            "signature": {
                "digest": signature,
                "sig_hash": transaction_hash,
                "public_key": self.service_config.public_key
            },
            "owner": self.service_config.owner,
            "phase": int(phase),
            "transaction_info": {
                "approved_transactions": map(lambda tx: str(tx["header"]["transaction_id"]), approved_transactions)
            }
        }
        if rejected_transactions:
            block_verification["transaction_info"]["rejected_transactions"] = \
                map(lambda tx: str(tx["header"]["transaction_id"]), rejected_transactions)

        verfication_db.insert_verification(block_verification)

    def sign_verifications(self, verifications, phase):
        block_id = None if len(verifications) == 0 else verifications[0]["block_id"]

        """Sign the passed set of transactions and return the sig JSON"""
        signature, verification_hash = sign_signatures(map(lambda verification: verification["signature"], verifications), self.service_config.private_key)
        # Create block verification data
        block_verification = {
            "verified_ts": int(time.time()),
            "block_id": block_id,
            "signature": {
                "digest": signature,
                "sig_hash": verification_hash,
                "public_key": self.service_config.public_key
            },
            "owner": self.service_config.owner,
            "phase": int(phase),
            "verification_info": {
                "approved_verifications": map(lambda verification: str(verification["verification_id"]), verifications)
            }
        }
        # Insert into database
        verfication_db.insert_verification(block_verification)

    ####INTERNAL METHODS###
    def _init_networking(self):
        pass

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
        #Prevent duplicate registration of the same phase index
        if config["phase"] not in self._configured_phases:
            self._configured_phases += [config["phase"]]
        else:
            raise Exception("Phase " + config["phase"] + " has already been registered.")

        if config["phase"] == 1:
            #Register the primary phase observer
            self._add_registration(ProcessingNode.PHASE_1_NAME, self._execute_phase_1, config)

            #Setup phase 1 cron
            trigger = CronTrigger(second='*/5')

            #setup the scheduler task
            def trigger_handler():
                self.notify(event_name=ProcessingNode.PHASE_1_NAME, current_block_id=get_current_block_id())

            #schedule task using cron trigger
            self._scheduler.add_job(trigger_handler, trigger)
        #TODO: implement other phases
        elif config["phase"] == 2:
            if ProcessingNode.PHASE_2_NAME not in self._registrations:
                self._registrations[ProcessingNode.PHASE_2_NAME] = []
            self._registrations[ProcessingNode.PHASE_2_NAME] += [{
                'callback': self._execute_phase_2,
                'config': config
            }]

        elif config["phase"] == 3:
            if ProcessingNode.PHASE_3_NAME not in self._registrations:
                self._registrations[ProcessingNode.PHASE_3_NAME] = []
            self._registrations[ProcessingNode.PHASE_3_NAME] += [{
                'callback': self._execute_phase_3,
                'config': config
            }]

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

        #schedule task using cron trigger
        self._scheduler.add_job(trigger_handler, trigger)

    def _observer_type_config_handler(self, config):
        if 'event_name' not in config:
            raise Exception("Observer config must have an event_name specified")
        if 'callback' not in config:
            raise Exception("Observer config must provide a callback function")

        self._add_registration(config['event_name'], config['callback'], config)

    def _execute_phase_1(self, config, current_block_id):
        """
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
        #Group transactions for last 5 seconds into current block id
        block_bound_lower_ts = get_block_time(current_block_id - BLOCK_FIXATE_OFFSET)
        print ("""Time bounds: %i - %i""" % (block_bound_lower_ts, block_bound_lower_ts + BLOCK_INTERVAL - 1))
        transaction_db.fixate_block(block_bound_lower_ts, block_bound_lower_ts + BLOCK_INTERVAL - 1, current_block_id)

        if 'approve_block' in config:
            return config['approve_block'](config, current_block_id)

        transactions = transaction_db.get_all(block_id=current_block_id)
        #Validate the schema and structure of the transactions
        valid_transactions, invalid_transactions = self.split_items(validate_transaction, transactions)
        #Use the custom approval code if configured, otherwise approve all valid transaction
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
            # sign approved transactions
            self.sign_transactions(1, approved_transactions)
            print("Phase 1 signed " + str(len(approved_transactions)) + " transactions")

        # update status of rejected transactions
        if len(rejected_transactions) > 0:
            for tx in rejected_transactions:
                tx["header"]["status"] = "rejected"
                transaction_db.update_transaction(tx)

    def _execute_phase_2(self, config, transactions):
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
        pass

    def _execute_phase_3(self, config):
        """
        * At this point, any participating processing nodes will have appended signed Phase 2 verification proof to the block.
        * Processing nodes participating in Phase 3 Verification may be a different set of nodes than the set of nodes participating in Phase 1 and Phase 2 Verification processes.
        * Processing nodes may be defined for the sole purpose of Phase 3 verification (e.g. for independent blockchain verification auditing purposes).
        * A participating node will verify that no invalid transaction has been included in the set of approved transaction.
        * A participating node will verify that all "approved" transactions are signed by their respective owner.
        * A node may perform extra validation steps on all transactions and verification units.
        * All signed "Phase 3 Signature Structures" will be grouped, concatenated, and cryptographically signed by the node.
        """
        pass


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
        parser.add_argument('-p', '--port', default = 8080)
        parser.add_argument('--debug', default = True, action = "store_true")
        parser.add_argument('--private-key', dest = "private_key", required = True, help = "ECDSA private key for signing")
        parser.add_argument('--public-key', dest = "public_key", required = True, help = "ECDSA public key for signing")

        logger().info("Parsing arguments")
        args = vars(parser.parse_args())

        private_key = args["private_key"]

        with open(private_key, 'r') as key:
            private_key = key.read()

        public_key = args["public_key"]

        with open(public_key, 'r') as key:
            public_key = key.read()

        port = args["port"]
        ProcessingNode([{
            "type": "phase",
            "phase": 1
        }], {
            "private_key": private_key,
            "public_key": public_key,
            "owner": "DTSS",
            "port": port
        }).start()

        #print('Connection Manager start')
        #network.ConnectionManager('localhost', port)
    finally:
        postgres.close_connection_pool()

# start calling f now and every 60 sec thereafter

if __name__ == '__main__':
    main()
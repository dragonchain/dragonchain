"""
Copyright 2017, Dragonchain Foundation

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

"""
                **trusted smart contract module**
smart contract code is run through this module under the assumption that the user is not delivering
invalid or malicious code.
"""

__author__ = "Joe Roets, Brandon Kite, Dylan Yelton, Michael Bachtel"
__copyright__ = "Copyright 2017, Dragonchain Foundation"
__license__ = "Apache"
__version__ = "2.0"
__maintainer__ = "Joe Roets"
__email__ = "joe@dragonchain.org"

import logging

from blockchain.db.postgres import smart_contracts_db as sc_dao
from blockchain.db.postgres import sub_to_db as sub_db
from blockchain.db.postgres import verification_db
from blockchain.db.postgres import transaction_db

import base64
import time
import uuid
from collections import defaultdict


def logger(name="verifier-service"):
    return logging.getLogger(name)


class SmartContractsHandler(object):
    def __init__(self, network=None, public_key=None):
        # processing nodes network
        self.network = network
        # processing node's public key
        self.public_key = public_key
        # reserved smart contract handler
        self.rsch = ReservedSmartContractsHandler(self.network, self.public_key)
        self.rtsc = {"TT_SUB_REQ": self.rsch.subscription_request,
                     "TT_PROVISION_SC": self.provision_sc,
                     "TT_PROVISION_TSC": self.provision_tsc,
                     "TT_PROVISION_SSC": self.provision_ssc,
                     "TT_PROVISION_LSC": self.provision_lsc,
                     "TT_PROVISION_BSC": self.provision_bsc}
        # user/business transaction smart contracts (txn_type => function)
        self.tsc = {}
        # subscription smart contracts
        self.ssc = {}
        # arbitrary/library smart contracts
        self.lsc = {}
        # broadcast receipt smart contracts
        self.bsc = {}

        # structure to hold smart contracts - sc_class => sc dict
        self.sc_container = {"tsc": self.tsc, "ssc": self.ssc, "lsc": self.lsc, "bsc": self.bsc}

        # load existing smart contracts from database
        self.load_scs()

    def provision_sc(self, transaction):
        return True

    def provision_tsc(self, transaction):
        """
        provision tsc class smart contract
        :param transaction: transaction to extract sc data from
        """
        status = False
        pl = transaction['payload']
        if "transaction_type" in pl and pl['transaction_type']:
            sc_key = pl['transaction_type']
            # insert new sc into database
            if self._insert_sc(pl, "tsc", sc_key):
                status = self._sc_provisioning_helper(pl, "tsc", sc_key)
        return status

    def provision_ssc(self, transaction):
        """
        provision ssc class smart contract
        :param transaction: transaction to extract sc data from
        """
        pl = transaction['payload']
        criteria = pl['criteria']
        sc_key = ""
        if "origin_id" in criteria:
            if "origin_id" in pl and pl['origin_id']:
                sc_key += pl['origin_id']
            else:
                return False
        sc_key += ":"
        if "transaction_type" in criteria:
            if "transaction_type" in pl and pl['transaction_type']:
                sc_key += pl['transaction_type']
            else:
                return False
        sc_key += ":"
        if "phase" in criteria:
            if "phase" in pl and pl['phase']:
                sc_key += str(pl['phase'])
            else:
                return False
        # insert new sc into database
        if not self._insert_sc(pl, "ssc", sc_key):
            return False
        return self._sc_provisioning_helper(pl, "ssc", sc_key)

    # TODO: implement lsc functionality
    def provision_lsc(self, transaction):
        """ provide name and python module to run sc """
        return True

    def provision_bsc(self, transaction):
        """
        provision bsc class smart contract
        :param transaction: transaction to extract sc data from
        """
        status = False
        pl = transaction['payload']
        if "phase" in pl and pl['phase']:
            sc_key = pl['phase']
            if self._insert_sc(pl, "bsc", sc_key):
                status = self._sc_provisioning_helper(pl, "bsc", sc_key)
        return status

    def _sc_provisioning_helper(self, pl, sc_class, sc_key):
        """
        insert sc code into appropriate dictionary
        :param pl: transaction payload to extract sc from
        :param sc_class: type of sc being dealt with (e.g. tsc, ssc, etc.)
        :param sc_key: transaction type
        """
        try:
            if 'smart_contract' in pl:
                sc = pl['smart_contract']
                sc_impl = sc[sc_class]
                if sc_impl:
                    try:
                        sc_impl = base64.standard_b64decode(sc_impl)
                    except TypeError:
                        raise Exception("The Smart Contract implementation for " + str(sc_key) +
                                        " must be base64 encoded.")

                    func = None
                    # define sc function
                    exec(sc_impl)
                    # store sc function for this txn type (sc_key)
                    self.sc_container[sc_class][sc_key] = func
                else:
                    logger().warning("No smart contract code provided...")
                    return False
            else:
                return False
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            logger().warning(message)
            return False
        return True

    def execute_tsc(self, transaction):
        txn_type = transaction["header"]["transaction_type"]
        try:
            return self.tsc[txn_type](transaction)
        except:
            logger().warning("An error occurred during tsc execution on transaction: %s", transaction['owner'])
            return False

    def execute_ssc(self, min_block_id, vr_limit, txn_limit):
        """ execute subscription smart contract """
        for sc_key in self.ssc.keys():
            (origin_id, txn_type, phase) = sc_key.split(":")
            vrs = verification_db.get_all(limit=vr_limit, origin_id=origin_id, phase=phase, min_block_id=min_block_id)
            #dedupe block ids
            block_ids = {v['block_id'] for v in vrs}
            #group vr's by block id
            block_vrs = defaultdict(list)
            for v in vrs:
                block_vrs[v['block_id']].append(v)

            # fetch all txns for each block
            for block_id in block_ids:
                #todo: filter by p1 signatory
                txns = transaction_db.get_all(transaction_type=txn_type, block_id=block_id, limit=txn_limit)
                # execute ssc for each vr in block
                for v in block_vrs[block_id]:
                    self.ssc[sc_key](txns, v)

    def execute_lsc(self):
        pass

    def execute_bsc(self, phase, vr):
        """ run broadcast smart contract on verification record if phase matches """
        if phase in self.bsc:
            self.bsc[phase](vr)

    def _insert_sc(self, pl, sc_class, sc_key):
        """ insert sc info into database """
        try:
            sc_dao.insert_sc(pl, sc_class, sc_key)
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            logger().warning(message)
            return False
        return True

    # FIXME: only load highest version sc to avoid overwriting
    def load_scs(self):
        """ load existing smart contracts from database """
        try:
            scs = sc_dao.get_all()
            for sc in scs:
                sc_class = sc['sc_class']
                sc_key = sc['sc_key']
                if sc_class in self.sc_container:
                    func = None
                    # define sc function
                    exec(sc['smart_contract'])
                    self.sc_container[sc_class][sc_key] = func
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            logger().warning(message)


class ReservedSmartContractsHandler(object):
    def __init__(self, network=None, public_key=None):
        # processing nodes network
        self.network = network
        # processing node's public key
        self.public_key = public_key

    def subscription_request(self, transaction):
        """
            attempts to make initial communication with subscription node
            param transaction: transaction to retrieve subscription info from
        """
        # check if given transaction has one or more subscriptions tied to it and inserts into subscriptions database
        if self.network and self.public_key:
            if "subscription" in transaction["payload"]:
                subscription = transaction["payload"]['subscription']
                try:
                    subscription_id = str(uuid.uuid4())
                    criteria = subscription['criteria']
                    phase_criteria = subscription['phase_criteria']
                    subscription['create_ts'] = int(time.time())
                    # store new subscription info
                    sub_db.insert_subscription(subscription, subscription_id)
                    # get subscription node
                    subscription_node = self.network.get_subscription_node(subscription)
                    # initiate communication with subscription node
                    if subscription_node:
                        subscription_node.client.subscription_provisioning(subscription_id, criteria, phase_criteria,
                                                                           subscription['create_ts'], self.public_key)
                    return True
                except Exception as ex:  # likely already subscribed
                    template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                    message = template.format(type(ex).__name__, ex.args)
                    logger().warning(message)
                    return False
        else:
            logger().warning("Could not fulfill subscription request: no network or public key provided.")
            return False
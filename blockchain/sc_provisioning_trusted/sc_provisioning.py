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

import logging

from blockchain.db.postgres import smart_contracts_db as sc_dao


def logger(name="verifier-service"):
    return logging.getLogger(name)


class SmartContractProvisioning(object):
    def __init__(self):
        self.rtsc = {"TT_SUB_REQ": self._subscription_request,
                     "TT_PROVISION_SC": self.provision_sc}
        # user/business transaction smart contracts
        self.tsc = {}
        # subscription smart contracts
        self.ssc = {}
        # arbitrary/library smart contracts
        self.lsc = {}
        # broadcast receipt smart contracts
        self.bsc = {}

    def provision_sc(self, transaction):
        return True

    def provision_tsc(self, transaction):
        """
        provision tsc type smart contract
        :param transaction: transaction to extract sc data from
        """
        pl = transaction['payload']
        txn_type = transaction['header']['transaction_type']
        # insert new sc into database
        if not self.insert_sc(pl, "tsc", txn_type):
            return False
        return self.sc_provisioning_helper(pl, "tsc")

    def provision_ssc(self, transaction):
        pl = transaction['payload']
        txn_type = transaction['header']['transaction_type']
        # insert new sc into database
        if not self.insert_sc(pl, "ssc", txn_type):
            return False
        return self.sc_provisioning_helper(pl, "ssc")

    def provision_lsc(self, transaction):
        return True

    def provision_bsc(self, transaction):
        return self.sc_provisioning_helper(transaction['payload'], "bsc")

    def sc_provisioning_helper(self, pl, sc_type):
        """
        insert sc code into appropriate dictionary
        :param pl: transaction payload to extract sc from
        :param sc_type: type of sc being dealt with (e.g. tsc, ssc, etc.)
        """
        try:
            if 'smart_contract' in pl:
                sc = pl['smart_contract']
                if sc[sc_type]:
                    func = None
                    # define sc function
                    exec (sc[sc_type])
                    # store sc function for this txn type
                    self.tsc[pl['transaction_type']] = func
                else:
                    logger().warning("No smart contract code provided...")
                    return False
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            logger().warning(message)
            return False
        return True

    def insert_sc(self, pl, sc_type, txn_type):
        """ insert sc info into database """
        try:
            sc_dao.insert_sc(pl, sc_type, txn_type)
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            logger().warning(message)
            return False
        return True

    def load_sc_keys(self):
        pass


if __name__ == '__main__':
    main()

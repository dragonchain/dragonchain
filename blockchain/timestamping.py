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

__author__ = "Joe Roets, Brandon Kite, Dylan Yelton, Michael Bachtel, Alex Benedetto, Lucas Ontivero"
__copyright__ = "Copyright 2016, Disney Connected and Advanced Technologies"
__license__ = "Apache"
__version__ = "2.0"
__maintainer__ = "Joe Roets"
__email__ = "joe@dragonchain.org"


"""
Module for storing data into the bitcoin blockchain transaction ontput scripts
"""

import bitcoin.rpc

from bitcoin import params
from bitcoin.core import *
from bitcoin.core.script import *

import requests
import logging

log = logging.getLogger(__name__)


class BitcoinTimestamper(): # IPoEStore
    """
    Stamps a data item in the bitcoin blockchain and also allows us to verifies the
    existence of a data item in a given bitcoin transaction output. For doing this
    a bitcoin node is required and available through RPC. The access data such as
    user name and password are read from ~/.bitcoin/bitcoin.conf configuration file

    usage example:
        fee_provider = BitcoinFeeProvider()
        stamper = BitcoinTimestamper("regtest", fee_provider)
        txid = stamper.persist("hello world!")
        assert stamper.ispersisted(txid, "hello world!"), "data item not present in the given txid"
    """
    MIN_FEE_BYTE = 60
    MAX_FEE_BYTE = 250
    P2PKH_SIGSCRIPT_SIZE = 105

    def __init__(self, network, fee_provider):
        """
        Initializes a instance for working against a bitcoin network.
        Args:
            network: mainnet, regtest, testnet
            fee_provider: suggests fee per bytes to pay
        """
        bitcoin.SelectParams(network)
        self.fee_provider = fee_provider


    def ispersisted(self, tx_id, data):
        """
        Verifies ``data`` item is on the bitcoin transaction identified by the ``tx_id``
        Args:
            tx_id: the bitcoin transaction id where the data is stored
            data: the item data we want to verify

        Returns:
            True if the ``data`` item is in the bitcoin transaction identified by ``tx_id``; otherwise False
        """
        log.info('Connection to local bitcoin node')
        proxy = bitcoin.rpc.Proxy()
        tx = proxy.getrawtransaction(tx_id, True)['tx']
        for vout in tx.vout:
            step = 'init'
            for op in vout.scriptPubKey:
                if step == 'init' and op == OP_RETURN:
                    step = 'waiting_data'
                    continue
                if step == 'waiting_data' and op == data:
                    return True
        return False


    def persist(self, data):
        """
        Persists data in the Bitcoin blockchain and returns and transaction id for future reference.

        Connects to the local bitcoin node using the bitcoin.conf file RPC username and password,
        requests the list of unspent transaction outputs (UTXO) and takes the one with less amount
        from being used as input in the new transaction.


        Args:
            data: the item data to be persisted

        Returns:
            A transaction id for referencing the saved data item in the transaction output
        """
        proxy = bitcoin.rpc.Proxy()
        utxo = sorted(proxy.listunspent(0), key=lambda x: hash(x['amount']))[-1]
        tx = self._build_timestamp_transaction(utxo, self.get_new_pubkey(), data)
        value_in = utxo['amount']

        fee_byte = self.fee_provider.recommended()
        fee_byte = max(fee_byte, self.MIN_FEE_BYTE)

        try:
            if fee_byte < self.MAX_FEE_BYTE:
                pass
        except:
            print "Fee too high"
            return

        new_tx = tx
        suggested_fee = (len(new_tx.serialize()) + self.P2PKH_SIGSCRIPT_SIZE) * fee_byte
        new_tx.vout[0].nValue = int(value_in - suggested_fee)
        r = proxy.signrawtransaction(new_tx)
        assert r['complete']
        new_tx = r['tx']
        suggested_fee = len(new_tx.serialize()) * fee_byte
        tx_id = proxy.sendrawtransaction(new_tx)
        log.info('Transaction sent')
        return tx_id


    def get_new_pubkey(self):
        """
        Requests a new bitcoin address and returns its public key
        """
        proxy = bitcoin.rpc.Proxy()
        address = proxy.getnewaddress()
        pubkey = proxy.validateaddress(address)['pubkey']
        return pubkey


    def _build_timestamp_transaction(self, output, change_pubkey, data):
        """
        Builds a bitcoin transaction with 1 input and 2 outputs:
            output 1 - the change output
            output 2 - the OP_RETURN + data output
        Args:
            output: the coin to use as input
            change_pubkey: change address' pubkey
            data: data item (a hash) to persist after the OP_RETURN opcode
        Returns:
            a bitcoin transaction that is candidate for being broadcast to the network
        """
        txins = [CTxIn(output['outpoint'])]
        change_out = CMutableTxOut(params.MAX_MONEY, CScript([change_pubkey, OP_CHECKSIG]))
        digest_out = [CMutableTxOut(0, CScript([OP_RETURN, data]))]
        txouts = [change_out] + digest_out
        tx = CMutableTransaction(txins, txouts)
        return tx


class BitcoinFeeProvider(object):
    """
    Provides estimated bitcoin fee using a 3rd party service.
    """
    FEE_URL = "https://bitcoinfees.21.co/api/v1/fees/recommended"
    def recommended(self):
        """
        provides an recommended fee per byte

        Return: the avg value between the estimated fastestFee value and the estimated
        halfHourFee value.
        """
        response = requests.get(self.FEE_URL)
        fees = response.json()
        calculated_fee = 0.5 * (int(fees["fastestFee"]) + int(fees["halfHourFee"]))
        return int(calculated_fee)
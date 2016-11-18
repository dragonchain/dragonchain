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
Primary service endpoint for blockchain node
"""
import json
import sys
import logging
import argparse
import tornado
import tornado.web
import tornado.ioloop
from db.postgres import postgres

from blockchain.util.crypto import sign_transaction, valid_transaction_sig

from blockchain.db.postgres import transaction_db as tx_dao

import uuid

import time


def format_error(category, msg):
    return json.dumps({"error": {"type": category, "details": msg}})


class TransactionHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        tornado.web.RequestHandler.__init__(self, *args, **kwargs)

    # TODO: consider storing original payload for hashing
    def post(self):
        txn = self.request.body
        log = self.application.log
        log.debug("Parsing JSON")

        try:
            txn = tornado.escape.json_decode(txn)
            txn["header"]["transaction_id"] = str(uuid.uuid4())
            txn["header"]["transaction_ts"] = int(time.time())
        except:
            log.error("Failed to parse JSON.  Details: " + str(sys.exc_info()[1]))
            self.clear()
            self.set_txn_status(log, 400)
            self.write(format_error("invalid input", "ERROR:  Failed to parse JSON\n"))
            return

        try:
            log.info("Validating the transaction")
            if not valid_vestal_transaction(txn):
                return False

            if valid_transaction_sig(txn):
                log.info("Signing the transaction")
                txn = sign_transaction("transaction-service",
                                       self.application.private_key,
                                       self.application.public_key, txn)

                tx_dao.insert_transaction(txn)
                self.set_header("Content-Type", "application/json")
                self.set_txn_status(log, 201)
                self.write(json.dumps({
                    "transaction_id": txn["header"]["transaction_id"]
                }))
                return
            else:  # TODO: add status function accepts status code number and status string
                self.set_txn_status(log, 400)
                return
        except:
            log.error(str(sys.exc_info()))
            self.clear()
            self.set_txn_status(log, 500)
            self.write(format_error("validation", str(sys.exc_info()[1])))

    def set_txn_status(self, log, status_code):
        if status_code == 400:
            log.error("400: Bad Request. The request could not be understood by the server due to malformed syntax.")
        elif status_code == 201:
            log.info("201: Created. The request has been fulfilled and resulted in a new resource being created.")
        elif status_code == 500:
            log.error("500: Internal Error: The server encountered an unexpected condition which prevented it from fulfilling the request.")
        self.set_status(status_code)


def valid_vestal_transaction(transaction):
    """ check if raw client transaction contains required fields """
    tx_header = transaction["header"]
    valid = True

    if not tx_header["transaction_type"]:
        valid = False
    if not tx_header["owner"]:
        valid = False

    return valid


class TransactionService(tornado.web.Application):
    def __init__(self, *args, **kwargs):

        self.private_key = kwargs["private_key"]
        del kwargs["private_key"]

        with open(self.private_key, 'r') as key:
            self.private_key = key.read()

        self.public_key = kwargs["public_key"]
        del kwargs["public_key"]

        with open(self.public_key, 'r') as key:
            self.public_key = key.read()

        self.log = kwargs["log"]
        del kwargs["log"]

        # constructor of base class
        tornado.web.Application.__init__(self, *args, **kwargs)


def run():

    logging.basicConfig(format="%(asctime)s %(levelname)s - %(message)s", level=logging.DEBUG)
    log = logging.getLogger("txn-service")
    log.info("Setting up argparse")
    parser = argparse.ArgumentParser(description='Process some integers.', prog='python -m blockchain')
    parser.add_argument('-p', '--port', default=8000)
    parser.add_argument('--debug', default=True, action="store_true")
    parser.add_argument('--private-key', dest="private_key", required=True, help="ECDSA private key for signing")
    parser.add_argument('--public-key', dest="public_key", required=True, help="ECDSA private key for signing")

    log.info("Parsing arguments")
    args = parser.parse_args()

    hdlrs = [
        (r"^/transaction$", TransactionHandler),
        (r"^/transaction/(.*)", TransactionHandler),
    ]

    log.info("Creating new tornado.web.Application")
    application = TransactionService(hdlrs,
        log = log,
        **vars(args))

    log.info("Starting transaction service on port %s" % args.port)
    application.listen(args.port)
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    run()
    postgres.close_connection_pool()

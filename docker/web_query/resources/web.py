#!/usr/bin/python
import json
import sys

import tornado
import tornado.ioloop
import tornado.web

from blockchain.txn import validate_json, \
                           sign_transaction, \
                           validate_transaction

from blockchain.db.postgres import transaction_db as tx_dao
from blockchain.db.postgres import verfication_db

def format_error(category, msg):
    return json.dumps({"error": { "type": category, "details": msg } })

class TransactionHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        tornado.web.RequestHandler.__init__(self, *args, **kwargs)
        self.query_fields = {
            'block_id': None,
            'transaction_type': None,
            'actor': None,
            'entity': None
        }

    def post(self):
        txn = self.request.body
        log = self.application.log
        log.debug("Parsing JSON")

        try:
            txn = tornado.escape.json_decode(txn)
        except:
            log.error("Failed to parse JSON.  Details: " + str(sys.exc_info()[1]))
            self.clear()
            self.set_status(400)
            self.write(format_error("invalid input", "ERROR:  Failed to parse JSON\n"))
            return

        try:
            log.info("Validating JSON")
            validate_json(txn)
        except:
            log.error(str(sys.exc_info()))
            self.clear()
            self.set_status(400)
            self.write(format_error("validation", str(sys.exc_info()[1])))
            return

        try:
            log.info("Signing the transaction")
            txn = sign_transaction("transaction-service", self.application.private_key, self.application.public_key, txn)
            log.info("Verifying the transaction")
            validate_transaction(txn)
            tx_id = tx_dao.insert_transaction(txn)
            self.set_status(201)
            self.write(json.dumps({
                "transaction_id": tx_id
            }))
        except:
            log.error(str(sys.exc_info()))
            self.clear()
            self.set_status(500)
            self.write(format_error("validation", str(sys.exc_info()[1])))

    def get(self, transaction_id=None):
        try:
            log = self.application.log
            rows = int(self.get_query_argument('rows', default='-1'))
            offset = int(self.get_query_argument('offset', default='-1'))
            if rows < 1:
                rows = None
            if offset < 1:
                offset = None

            results = []
            if transaction_id:
                results = tx_dao.get(transaction_id)
            else:
                query = {}
                for field, default in self.query_fields.iteritems():
                    value = self.get_query_argument(field, default)
                    if value:
                        query[field] = value

                for tx in tx_dao.get_all(limit=rows, offset=offset, **query):
                    results += [tx]
            self.write(json.dumps(results))
        except:
            log.error(str(sys.exc_info()))
            self.clear()
            self.set_status(500)
            self.write(format_error("server error", str(sys.exc_info()[1])))

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

class BlockVerificationHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        tornado.web.RequestHandler.__init__(self, *args, **kwargs)

    def get(self, block_id=None):
        rows = int(self.get_query_argument('rows', default='-1'))
        offset = int(self.get_argument('offset', default='-1'))
        if rows < 1:
            rows = None
        if offset < 1:
            offset = None
        results = [verification for verification in verfication_db.get_all(limit=rows, offset=offset, block_id=block_id)]
        self.write(json.dumps(results))


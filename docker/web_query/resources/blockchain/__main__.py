"""
Primary service endpoint for blockchain node
"""
import sys
import logging
import argparse

def logger(name = "txn-service"):
    return

import tornado.ioloop
import tornado.web
import tornado
from db.postgres import postgres

from blockchain.web import TransactionService, TransactionHandler, BlockVerificationHandler

def run():

    logging.basicConfig(format="%(asctime)s %(levelname)s - %(message)s", level = logging.DEBUG)
    log = logging.getLogger("txn-service")
    log.info("Setting up argparse")
    parser = argparse.ArgumentParser(description='Process some integers.', prog='python -m blockchain')
    parser.add_argument('-p', '--port', default = 8080)
    parser.add_argument('--debug', default = True, action = "store_true")
    parser.add_argument('--private-key', dest = "private_key", required = True, help = "RSA private key for signing")
    parser.add_argument('--public-key', dest = "public_key", required = True, help = "RSA private key for signing")

    log.info("Parsing arguments")
    args = parser.parse_args()

    hdlrs = [
        (r"^/transaction$", TransactionHandler),
        (r"^/transaction/(.*)", TransactionHandler),
        (r"^/verification$", BlockVerificationHandler),
        (r"^/verification/(.*)", BlockVerificationHandler),
    ]

    log.info("Creating new tornado.web.Application")
    application = TransactionService(hdlrs,
        log = log,
        **vars(args))

    log.info("Starting transaction service on port %d" % args.port)
    application.listen(args.port)
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    run()
    postgres.close_connection_pool()



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
Primary query service for blockchain node
"""
import json
import sys
import logging
import argparse

import tornado
import tornado.web
import tornado.ioloop
from db.postgres import postgres

from blockchain.db.postgres import transaction_db as tx_dao
from blockchain.db.postgres import verfication_db


def format_error(category, msg):
    return json.dumps({"error": { "type": category, "details": msg } })


class QueryHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        tornado.web.RequestHandler.__init__(self, *args, **kwargs)
        self.query_fields = {
            'block_id': None,
            'transaction_type': None,
            'create_ts': None,
            'transaction_ts': None,
            'business_unit': None,
            'family_of_business': None,
            'line_of_business': None,
            'signature': None,
            'status': None,
            'actor': None,
            'entity': None,
            'owner': None
        }

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
            self.set_header("Content-Type", "application/json")
            self.write(json.dumps(results))
        except:
            log.error(str(sys.exc_info()))
            self.clear()
            self.set_status(500)
            self.write(format_error("server error", str(sys.exc_info()[1])))


class QueryService(tornado.web.Application):
    def __init__(self, *args, **kwargs):
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

def run():

    logging.basicConfig(format="%(asctime)s %(levelname)s - %(message)s", level = logging.DEBUG)
    log = logging.getLogger("txn-service")
    log.info("Setting up argparse")
    parser = argparse.ArgumentParser(description='Process query info.', prog='python -m blockchain')
    parser.add_argument('-p', '--port', default = 8080)
    parser.add_argument('--debug', default = True, action = "store_true")

    log.info("Parsing arguments")
    args = parser.parse_args()

    query_hdlrs = [
        (r"^/transaction", QueryHandler),
        (r"^/transaction/(.*)", QueryHandler),
        (r"^/verification$", BlockVerificationHandler),
        (r"^/verification/(.*)", BlockVerificationHandler),
    ]

    log.info("Creating new tornado.web.Application")
    application = QueryService(query_hdlrs,
        log = log,
        **vars(args))

    log.info("Starting query service on port %s" % args.port)
    application.listen(args.port)
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    run()
    postgres.close_connection_pool()

#!/usr/bin/env python
#

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


import sys
import argparse
import logging
import httplib
import json
import time

seen = []


def run():
    logging.basicConfig(format="%(asctime)s %(levelname)s - %(message)s", level=logging.DEBUG)
    log = logging.getLogger("transaction-viewer")

    log.info("Setting up argparse")

    parser = argparse.ArgumentParser(description='Watch live blockchain transactions.', prog='')
    parser.add_argument('-s', '--server', required=False, default="blockchain.cloud.corp.dig.com", help="Query Service server.")
    parser.add_argument('-p', '--port', default=8080)
    parser.add_argument('--debug', default=True, action = "store_true")
    parser.add_argument('-c', '--criteria', dest="criteria", required=False, help="Query criteria as URL query string.")
    parser.add_argument('-t', '--polling-time-delay', dest="polling_time", required=False, help="Time delay in seconds between query requests.")

    log.info("Parsing arguments")
    args = parser.parse_args()
    print(args)

    while True:
        conn = httplib.HTTPConnection(args.server, args.port)
        url = "/transaction?" + args.criteria
        conn.request("GET", url)
        resp = conn.getresponse()
        resp_json = resp.read()

        # print(resp.status)
        # print(resp.reason)

        data = json.loads(resp_json)

        # print(len(data))

        for n in data:
            txid = n['header']['transaction_id']
            if txid not in seen:
                print
                print json.dumps(n, indent=2)
                seen.append(txid)

        time.sleep(int(args.polling_time))
        sys.stdout.write('.',)
        sys.stdout.flush()


if __name__ == "__main__":
    run()




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

""" only used for manually inserting data into nodes table """
from blockchain.db.postgres import network_db as net_dao
from blockchain.network import Node
import os
import uuid
import argparse
import json
import requests
import time
import binascii
import os
from base64 import urlsafe_b64encode, urlsafe_b64decode
from Crypto.Cipher import AES
from Crypto import Random

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s: s[:-ord(s[len(s) - 1:])]
base64pad = lambda s: s + '=' * (4 - len(s) % 4)
base64unpad = lambda s: s.rstrip("=")

print('"required arguments: --owner="NAME" --host="IP" --port="PORT" --phases="BINARY" --node_id="UUID" --pass="PASSWORD"')

def aes_encrypt(plaintext):
   data = '../key.pem'
   key = open(data, "r")
   dragonkey = key.read()
   iv = Random.new().read(BS)
   obj = AES.new(dragonkey, AES.MODE_CFB, iv, segment_size=AES.block_size * 8)
   ciphertext = obj.encrypt(pad(str(plaintext)))
   return base64unpad(urlsafe_b64encode(iv + ciphertext))

def load_required_nodes(owner, host, port, phase, node_id, passw):
    """
    manually insert network node into database
    Args:
        owner: node owner
        host: node host
        port: node port
        phases: node phase
        node_id: node node_id
        passw: node passw
    """
    node = Node(node_id, owner, host, port, phase)
    try:
        net_dao.insert_node(node)
    except Exception as e:
        print(e)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process node data.')
    parser.add_argument('--owner', default="NemoTechnologies")
    parser.add_argument('--host', default="35.193.45.37")
    parser.add_argument('--port', default="8080")
    parser.add_argument('--phases', default="00001")
    parser.add_argument('--node_id', default="2228237e-ce89-11e7-95ba-178c4babec33")
    parser.add_argument('--pass', default="ailuuhsighslgjshldgjhlifghslkjdghsldjghslkfjhgsldkfjghsldfgjhslfjgh")
    args = vars(parser.parse_args())

    owner = args['owner']
    host = args['host']
    port = args['port']
    phase = args['phases']
    node_id = args['node_id']
    passw = args['pass']
    load_required_nodes(owner, host, port, phase, node_id, passw)
    # send subscription
    postpost = "http://localhost:81/transaction"
    rawdata = "subscriptiontemplate.json"
    plain = open(rawdata, "r")
    opened = plain.read()
    nodeid = opened.replace("IIIIIIIII", node_id)
    if (phase == "00001"):
        phasei = str("1")
    if (phase == "00010"):
        phasei = str("2")
    if (phase == "00011"):
        phasei = str("3")
    if (phase == "00100"):
        phasei = str("4")
    if (phase == "00101"):
        phasei = str("5")
    phased = nodeid.replace("PPPPPPPPP", phasei)
    ported = phased.replace("OOOOOOOOO", port)
    hosted = ported.replace("HHHHHHHHH", host)
    owned = hosted.replace("ZZZZZZZZZ", owner)
    passed = owned.replace("DDDDDDDDD", passw)
    timestamp = int(time.time())
    times = str(timestamp)
    timestamped = passed.replace("XXXXXXXXX", times)
    print(timestamped)
    decrypted = timestamped
    encrypted = aes_encrypt(decrypted)
    headers = {'Access-Control-Allow-Methods': 'POST', 'Allow': 'POST'}
    rt = requests.post(postpost, data=encrypted, headers=headers)
    print(rt.text)
    print(rt)

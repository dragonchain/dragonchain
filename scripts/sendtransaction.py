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
def aes_encrypt(plaintext):
    data = '../key.pem'
    key = open(data, "r")
    dragonkey = key.read()
    iv = Random.new().read(BS)
    obj = AES.new(dragonkey, AES.MODE_CFB, iv, segment_size=AES.block_size * 8)
    ciphertext = obj.encrypt(pad(str(plaintext)))
    return base64unpad(urlsafe_b64encode(iv + ciphertext))

postpost = "http://localhost:81/transaction"
rawdata = input("INPUT A JSON FILENAME TO SEND, IT -MAY- NEED QUOTES: ")
plain = open(rawdata, "r")
opened = plain.read()
timestamp = int(time.time())
times = str(timestamp)
timestamped = opened.replace("XXXXXXXXX", times)
print(timestamped)
decrypted = json.dumps(timestamped)
encrypted = aes_encrypt(decrypted)
headers = {'Access-Control-Allow-Methods': 'POST', 'Allow': 'POST'}
rt = requests.post(postpost, data=encrypted, headers=headers)
print(rt.text)
print(rt)

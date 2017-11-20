import json
import requests
import time
import binascii
import os
from Crypto.Cipher import AES
import base64
def aes_encrypt(plaintext):
    data = '../key.pem'
    key = open(data, "r")
    dragonkey = key.read()
    print(dragonkey)
    obj = AES.new(dragonkey, AES.MODE_CBC, os.urandom(16))
    length = 16 - (len(plaintext) % 16)
    plaintext += chr(length)*length
    ciphertext = obj.encrypt(plaintext)
    return ciphertext

postpost = "http://localhost:81/transaction"
rawdata = input("INPUT A JSON FILENAME TO SEND, IT -MAY- NEED QUOTES: ")
print(rawdata)
plain = open(rawdata, "r")
opened = plain.read()
timestamp = time.time()
times = str(timestamp)
timestamped = opened.replace("XXXXXXXXX", times)
decrypted = json.dumps(timestamped)
encrypted = aes_encrypt(decrypted)
headers = {'Access-Control-Allow-Methods': 'POST', 'Allow': 'POST'}
rt = requests.post(postpost, data=encrypted, headers=headers)
print(rt.text)
print(rt)

import requests
import json
import time
getget = 'http://localhost:80/transaction'
postpost = 'http://localhost:81/transaction'


timestamp = int(time.time())
times = str(timestamp)

js0n = {'header': {'business_unit': 'a3e13076-8683-11e6-97a9-3c970e3bee11', 'family_of_business': 'Test Business Family', 'line_of_business': 'My Business', 'transaction_ts': times, 'transaction_type': 'TT_REQ', 'actor': 'c26dd972-8683-11e6-977b-3c970e3bee11', 'owner': 'Test Node', 'entity': 'c78f4526-8683-11e6-b1c6-3c970e3bee11', 'transaction_id': '8a864b59-46e3-4c9b-8dfd-9d9a2bd4b754', 'create_ts': times}, 'payload': {'action': {'amount': '5.0', 'artifact_id': '12345', 'name': 'Test Payload'}, 'source': 'f36c9086-8683-11e6-80dc-3c970e3bee11'}}
js1n = {'header': {'business_unit': 'a3e13076-8683-11e6-97a9-3c970e3bee11', 'family_of_business': 'Test Business Family', 'line_of_business': 'My Business', 'transaction_ts': times, 'transaction_type': 'TT_REQ', 'actor': 'c26dd972-8683-11e6-977b-3c970e3bee11', 'owner': 'Test Node', 'entity': 'c78f4526-8683-11e6-b1c6-3c970e3bee11', 'transaction_id': '8a864b59-46e3-4c9b-8dfd-9d9a2bd4b754', 'create_ts': times}, 'payload': {'action': {'amount': '5.0', 'artifact_id': '12345', 'name': 'Test Payload'}, 'source': 'f36c9086-8683-11e6-80dc-3c970e3bee11'}}
js2n = {"header":{"create_ts":times,"business_unit":"a3e13076-8683-11e6-97a9-3c970e3bee11","family_of_business":"Test Business Family","line_of_business":"My Business","owner":"Test Node","transaction_type":"TT_PROVISION_TSC","actor":"c26dd972-8683-11e6-977b-3c970e3bee11","entity":"c78f4526-8683-11e6-b1c6-3c970e3bee11"},"payload":{"smart_contract":{"transaction_type":"LOCATION_RECORD","implementation":"trusted","tsc":"ZGVmIGZ1bmMoc2VsZiwgdHJhbnNhY3Rpb24pOiANCiAgICBwYXlsb2FkID0gdHJhbnNhY3Rpb25bInBheWxvYWQiXQ0KICAgIGlmICJsYXQiIG5vdCBpbiBwYXlsb2FkIG9yICJsb25nIiBub3QgaW4gcGF5bG9hZCBvciAidGltZXN0YW1wIiBub3QgaW4gcGF5bG9hZDoNCiAgICAgICAgcmV0dXJuIEZhbHNlDQoNCiAgICBsYXQgPSBmbG9hdChwYXlsb2FkWyJsYXQiXSkNCiAgICBsb25nID0gZmxvYXQocGF5bG9hZFsibG9uZyJdKQ0KICAgIHJldHVybiBsYXQgPj0gLTkwIGFuZCBsYXQgPD0gOTAgYW5kIGxvbmcgPj0gLTE4MCBhbmQgbG9uZyA8PSAxODA="},"version":1}}
js3n = {"header":{"create_ts":times,"business_unit":"a3e13076-8683-11e6-97a9-3c970e3bee11","family_of_business":"Test Business Family","line_of_business":"My Business","owner":"Test Node","transaction_type":"LOCATION_RECORD","entity":"c78f4526-8683-11e6-b1c6-3c970e3bee11"},"payload":{"lat":25.0,"long":-71.0,"timestamp":times}}
headers = {'Access-Control-Allow-Methods': 'POST', 'Allow': 'POST'}
rt = requests.post(postpost, data=json.dumps(js2n), headers=headers)



# GET transaction
rg = requests.get(getget)

# Response, status etc
print(rt.text)
print(rt.status_code)
print(rg.text)
print(rg.status_code)

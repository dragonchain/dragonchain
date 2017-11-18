import requests
import json
import time
getget = 'http://localhost:80/transaction'
postpost = 'http://localhost:81/transaction'


timestamp = int(time.time())
times = str(timestamp)

js0n = {"header":{"create_ts":times,"business_unit":"","family_of_business":"Nemo Technologies","line_of_business":"Market Simulations","owner":"TheRoboKitten","transaction_type":"Simulation","actor":"Zenbot4","entity":"ZenDev"},"payload":{"Command":"./zenbot.sh sim","Result":"100%","Notes":""}}
headers = {'Access-Control-Allow-Methods': 'POST', 'Allow': 'POST'}
rt = requests.post(postpost, data=json.dumps(js0n), headers=headers)



# GET transaction
rg = requests.get(getget)

# Response, status etc
print(rt.text)
print(rt.status_code)
print(rg.text)
print(rg.status_code)

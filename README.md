# ZenChain - The DragonChain Fork

The Dragonchain platform attempts to simplify integration of real business applications onto a blockchain. Providing features such as easy integration, protection of business data, fixed 5 second blocks, currency agnosticism, and interop features, Dragonchain shines a new and interesting light on blockchain technology.

#### No blockchain expertise required!
Based on DragonChain, all rights to this software are copyright to Disney.

1. Ease of integration of existing systems 
1. Ease of development for traditional engineers and coders unfamiliar with blockchain, 
distributed systems, and cryptography 
1. Client server style and simple RESTful integration points for business integration 
1. Simple architecture (flexible and usable for unforeseen applications) 
1. Provide protection of business data by default
1. Allow business focused control of processes
1. Fixed length period blocks 
1. Short/fast blocks 
1. Currency agnostic blockchain (multi­currency support) 
1. No base currency 
1. Interoperability with other blockchains public and private 
1. Adoption of standards as they become available (see ​W3C Blockchain Community 
Group blockchain standardization​) 


## Quick Links
* [Dragonchain Organization](https://dragonchain.github.io/)
* [Dragonchain Architecture Document](https://dragonchain.github.io/architecture) - [PDF](https://dragonchain.github.io/doc/DragonchainArchitecture.pdf)
* [Use Cases](https://dragonchain.github.io/blockchain-use-cases)
* [Disney Blockchain Standardization Notes](https://dragonchain.github.io/blockchain-standardization) - [W3C](https://github.com/w3c/blockchain/blob/master/standards.md)

## Support

* Slack Team: [Dragonchain Slack Team](https://dragonchain.slack.com/) sign up: [![Slack Status](https://dragonchain-slack.herokuapp.com/badge.svg)](https://dragonchain-slack.herokuapp.com)
* Slack Support Channel: [#support](https://dragonchain.slack.com/messages/support/)
* Email: support@dragonchain.org

## Maintainer
Joe Roets (j03)
joe@dragonchain.org

# Setup and Installation

```git clone https://github.com/TheRoboKitten/TheRoboKitten.Github.io.git zenchain/```

Then do:

```cd zenchain/```

Then do:

```sudo chmod +x install.sh```

Then do:

```sudo ./install.sh```

Read the output at the end of the setup for more information. Check scripts directory for more information.
Make sure to establish IPTABLES and ROUTE to docker bi-directional:
Follow this template, but it will more than likely need to be modified on a per-host basis:

```
iptables -A FORWARD -i docker0 -o eth0 -j ACCEPT

iptables -A FORWARD -i eth0 -o docker0 -j ACCEPT

route add -net <dockerip> netmask <net mask> gw <docker's host>
```

Then,

If you want to send or provision a transaction:

#### To provision a subscription smart contract transaction:

```cd scripts/```

```sudo ./provisiontx.sh```

Notes on provisioning subscription smart contract transactions:

Template:

```
{
  "header": {
    "create_ts": XXXXXXXXX,
    "business_unit": "NemoTechnologies",
    "family_of_business": "NemoTechnologies",
    "line_of_business": "NemoTechnologies",
    "owner": "NemoTechnologies",
    "transaction_type": "TT_PROVISION_SSC",
    "actor": "NemoTechnologies",
    "entity": "NemoTechnologies"
  },
  "payload": {
    "phase": 2,
    "smart_contract": {
      "transaction_type": "NemoTechnologies",
      "ssc": "ZGVmIGZ1bmMoc2VsZiwgdHJhbnNhY3Rpb24pOiByZXR1cm4gVHJ1ZQ==" <- Base 64 encoded python data aggregation command!
    },
    "criteria": ["phase"],
    "test": "print 'TEST'",
    "requirements": ["uuid", "time"],
    "version": 1
  }
}
```
The flow is: 

#### TT_PROVISION_SSC -> payload -> TT_PROVISION_SSC -> SSC -> Base64 Decode aggregate command -> Returns True -> Command to aggregate and verify transactions is stored in database for trusted future transactions.

In this case the base64 command is:

```
def func(self, transaction): return True
```

In theory, you could run any python code here to check or execute future transactions once base-64 decoded. But it MUST START WITH:

```def func(self, transaction):```

# The Below Notes Are In-Progress!

#### To send a Subscription Smart Contract transaction:

```cd scripts/```

```sudo ./sendtx.sh```

Notes on Subscription Smart Contract transactions:

Template:

```
{
  "header": {
    "create_ts": XXXXXXXXX, <--- Is current epoch in seconds `date +"%s"`
    "business_unit": "NemoTechnologies",
    "family_of_business": "NemoTechnologies",
    "line_of_business": "NemoTechnologies",
    "owner": "NemoTechnologies",
    "transaction_type": "NemoTechnologies",
    "entity": "Some data to serve as an index"
  },
  "payload": {
    "command": "Some data to be checked or stored",
    "timestamp": XXXXXXXXX <--- Is current epoch in seconds `date +"%s"`
  }
}
```

#### As a note to send a POST request in python, some checks must be made for access control in the HTML header (not the HTML payload!)

Example:

```
import time
import requests
import json
postpost = "http://localhost:81/transaction" <---- NOTE NO TRAILING SLASH
timestamp = time.time() <---- EPOCH IN SECONDS
times = str(timestamp) <---- STRINGIFY TIMESTAMP FOR JSON
js0n = {"header":{"create_ts":times,"business_unit":"NemoTechnologies","family_of_business":"NemoTechnologies","line_of_business":"NemoTechnologies","owner":"NemoTechnologies","transaction_type":"TT_PROVISION_SSC","actor":"NemoTechnologies","entity":"NemoTechnologies"},"payload":{"phase":2,"smart_contract":{"transaction_type":"NemoTechnologies","ssc":"ZGVmIGZ1bmMoc2VsZiwgdHJhbnNhY3Rpb24pOiByZXR1cm4gVHJ1ZQ=="},"criteria":["phase"],"test":"print 'TEST'","requirements":["uuid","time"],"version":1}}

headers = {'Access-Control-Allow-Methods': 'POST', 'Allow': 'POST'} <------- SEE HERE

rt = requests.post(postpost, data=json.dumps(js0n), headers=headers)

print(rt.status)
print(rt.text)
print(rt)
```

#### To make a curl POST request to port 81 in bash:

As an example:

```
#!/bin/bash
str=`cat provisionTSC.json`
find="XXXXXXXXX"
replace=`date +"%s"`
result=${str//$find/$replace}
echo "$result"

curl -H 'Accept-Encoding: gzip,deflate' -X POST http://localhost:81/transaction -d "$result"
```

#### Navigate to your http://localhost:80/transaction to view transactions or http://localhost:80/transaction/TRANSACTIONID to view a transaction.

#### Or to view live transactions, navigate to scripts/ then run:

```python tx-viewer.py```


# That's pretty much it! Have fun!

# Contribution

Dragonchain uses a standard Feature Branch Workflow.

All feature development should take place in Git branch dedicated to that feature. A feature branch should be named starting with the ticket ID followed by a dash and a short description.

Issues are tracked within Github: [Dragonchain Issues](https://github.com/dragonchain/dragonchain/issues)

## Formatting

Code should follow the [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/) for Python code where possible. 

## Contributors

- [Joe Roets - Principal Architect / Vision](https://www.linkedin.com/in/j0j0r0)
- [Eileen Quenin - Product Manager / Evangelist](https://www.linkedin.com/in/eileenquenin)
- [Brandon Kite - Lead Developer](https://www.linkedin.com/in/bkite)
- [Dylan Yelton - Developer](https://www.linkedin.com/in/dylan-yelton-b11ba5aa)
- [Alex Benedetto - Developer](https://www.linkedin.com/in/alex-benedetto-6175048b)
- [Michael Bachtel - DevOps / Developer](https://www.linkedin.com/in/michael-bachtel-617b7b2)
- [Lucas Ontivero - Developer](https://ar.linkedin.com/in/lucasontivero)
- [Adam Bronfin - Developer / Reviewer](https://www.linkedin.com/in/adam-bronfin-694a7440)
- [Benjamin Israelson - Developer / Reviewer](https://www.linkedin.com/in/benjaminisraelson)
- [Forrest Fisher - Program Manager](https://www.linkedin.com/in/forrestfisher)
- [Robbin Schill - Program Manager](https://www.linkedin.com/in/robbin-schill-a798044)
- [Krassi Krustev - Developer](https://www.linkedin.com/in/krassimir-krustev-252483ab)
- [Rob Eickmann - iOS Developer](https://www.linkedin.com/in/roberte3)
- [Sean Ochoa - DevOps / Sysadmin](https://www.linkedin.com/in/seanochoa)
- [Paul Sonier - Developer / Reviewer](https://www.linkedin.com/in/paul-sonier-18135b2)
- [Kevin Schumacher - Artist / Web Design](https://www.linkedin.com/in/schubox)
- [Brian J Wilson - Architect](https://www.linkedin.com/in/brian-wilson-9325a776)
- [Mike De'Shazer - Developer / Reviewer](https://kr.linkedin.com/in/mikedeshazer)
- [Tai Kersten - Developer / Reviewer](https://kr.linkedin.com/in/tai-kersten-bb460412a/en)
- Steve Owens - Reviewer
- Mark LaPerriere - Reviewer
- Kevin Duane - Reviewer
- Chris Moore - Reviewer

# Disclaimer

The comments, views, and opinions expressed in this forum are those of the authors and do not necessarily reflect the official policy or position of the Walt Disney Company, Disney Connected and Advanced Technologies, or any affiliated companies.

All code contained herein is provided “AS IS” without warranties of any kind. Any implied warranties of non-infringement, merchantability, and fitness for a particular purpose are expressly disclaimed by the author(s).

# License

```
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
```

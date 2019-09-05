<div align="center">
<img width=300px height=300px src="https://dragonchain.com/static/media/dragonchain-logo-treasure.png" alt="Dragonchain Logo">

# Dragonchain

[![Build Status](https://img.shields.io/travis/dragonchain/dragonchain)](https://travis-ci.org/dragonchain/dragonchain)
[![Test Coverage](https://img.shields.io/codeclimate/coverage/dragonchain/dragonchain)](https://codeclimate.com/github/dragonchain/dragonchain/test_coverage)
[![Code Style Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)
[![License](https://img.shields.io/badge/license-Apache%202.0-informational.svg)](https://github.com/dragonchain/dragonchain/blob/master/LICENSE)
![Banana Index](https://img.shields.io/endpoint.svg?url=https%3A%2F%2Fdragonchain-core-docs.dragonchain.com%2Fbanana-shield.json)

The Dragonchain platform simplifies the integration of real business applications onto a blockchain.
Providing features such as easy integration, protection of business data, fixed 5 second blocks, currency agnosticism,
and public blockchain interoperability, Dragonchain shines a new and interesting light on blockchain technology.

**No blockchain expertise required!**

</div>

## 🔗 Quick Links

- [Project Documentation](https://dragonchain-core-docs.dragonchain.com/latest/)
- [Dragonchain Console](https://console.dragonchain.com/)
- [Dragonchain Inc](https://dragonchain.com/)
- [Bug and Security Bounty Program](https://dragonchain.com/bug-and-security-bounty)
- [Project Bounty Program](https://dragonchain.com/strategic-projects-bounty)
- [Dragonchain Academy](https://academy.dragonchain.org/)
- [Dragonchain Blog](https://dragonchain.com/blog)
- [Dragonchain Architecture Document](https://dragonchain.com/assets/Dragonchain-Architecture.pdf)
- [Use Cases](https://dragonchain.com/blockchain-use-cases)

## 📝 Documentation

Please read the [docs](https://dragonchain-core-docs.dragonchain.com/latest/) for further details and documentation.

The documentation is intended for developers wishing to learn about and contribute to the Dragonchain core platform itself.

For _interaction_ with the Dragonchain, we recommend signing up for a [Dragonchain Console](https://console.dragonchain.com)
account and testing with our managed service, as it will be easier for getting started with developing _on top of_ dragonchain
(rather than developing the actual Dragonchain core platform).

For interaction and using the Dragonchain, check out the SDKs (or CLI) and their relevant documentation instead:

- Python: [SDK](https://pypi.org/project/dragonchain-sdk/) - [Documentation](https://python-sdk-docs.dragonchain.com/latest/)
- Javascript: [SDK](https://www.npmjs.com/package/dragonchain-sdk) - [Documentation](https://node-sdk-docs.dragonchain.com/latest/)
- Golang: [SDK](https://github.com/dragonchain/dragonchain-sdk-go) - [Documentation](https://godoc.org/github.com/dragonchain/dragonchain-sdk-go)
- CLI: [Link](https://www.npmjs.com/package/dctl)

## 🖥️ Development

Dragonchain is implemented in Python 3, packaged into container images with Docker, and intended to be run on Kubernetes (at the moment).

The [tools.sh](/tools.sh) script is used to assist in various development functions such as installing dependencies,
automatically formatting/linting code, running tests, etc. Simply run `./tools.sh` with no parameters to view what it
can do.

In order to develop locally you should be able to run `./tools.sh full-test` and have all checks pass. For this, a few requirements should be met:

1. Ensure that you have python 3.7 installed locally
1. Install OS dependencies for building various python package dependencies:
   - On an arch linux system (with pacman): `./tools.sh arch-install`
   - On a debian-based linux system (with apt): `./tools.sh deb-install` (Note on newer Ubuntu installations
     you may need to install `libsecp256k1-dev` if the secp256k1 python package fails to build)
   - On a Mac (with brew): `./tools.sh mac-install`
1. Install the python requirements: `./tools.sh pip-install`
   (Note this will install the python packages to the current user's site-packages.
   For a python venv, follow the steps below)

### Using a Python Virtual Environment

It is highly recommended to use a python virtual environment rather than simply installing the python
package requirements to your global environment. This allows the required packages for this project
to be separated from the rest of the (potentially conflicting) packages from the rest of the system.

In order to do this, instead of step 3 above, perform the following steps:

1. Ensure you have python venv installed, and run `python3.7 -m venv .venv`
1. Activate the virtual environment in your shell by running `source .venv/bin/activate`
1. Upgrade the setup dependencies for the virtual environment: `pip install -U pip setuptools`
1. Install the core dependencies: `pip install -r requirements.txt`
1. Install the dev dependencies: `pip install -U -r dev_requirements.txt`

### Other Information

For more information, including a deeper dive on the architecture/code structure, please read the [docs](https://dragonchain-core-docs.dragonchain.com/latest/).

## 🚀 Contributing

Want to make some money for helping the project?
We have project, bug, and security bounty programs which we invite anyone to participate in.
Details for these programs can be found here:

- [Bug and Security Bounty Program](https://dragonchain.com/bug-and-security-bounty)
- [Project Bounty Program](https://dragonchain.com/strategic-projects-bounty)

For more info on contributing, please read the [contributing](/CONTRIBUTING.md) document.

## ✔️ Support

- Developer Chat: [Dragonchain Slack](https://forms.gle/ec7sACnfnpLCv6tXA)
- General Dragonchain Chat: [Dragonchain Telegram](https://t.me/dragontalk)
- Email: support@dragonchain.com

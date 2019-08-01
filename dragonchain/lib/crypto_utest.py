# Copyright 2019 Dragonchain, Inc.
# Licensed under the Apache License, Version 2.0 (the "Apache License")
# with the following modification; you may not use this file except in
# compliance with the Apache License and the following modification to it:
# Section 6. Trademarks. is deleted and replaced with:
#      6. Trademarks. This License does not grant permission to use the trade
#         names, trademarks, service marks, or product names of the Licensor
#         and its affiliates, except as required to comply with Section 4(c) of
#         the License and to reproduce the content of the NOTICE file.
# You may obtain a copy of the Apache License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the Apache License with the above modification is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the Apache License for the specific
# language governing permissions and limitations under the Apache License.

import copy
import unittest
from base64 import b64decode

from secp256k1 import PrivateKey

from dragonchain.lib import crypto
from dragonchain.lib.dto import transaction_model
from dragonchain.lib.dto import l1_block_model
from dragonchain.lib.dto import l2_block_model
from dragonchain.lib.dto import l3_block_model
from dragonchain.lib.dto import l4_block_model
from dragonchain.lib.dto import l5_block_model

# Don't change this private key or tests will break
key = PrivateKey(privkey=b64decode("9oerV8bGxL+PyujfNEu2UJB1CjkjZ+XNcR7G0RMfSIc="), raw=True)
blake2b = crypto.SupportedHashes.blake2b
sha256 = crypto.SupportedHashes.sha256
sha3_256 = crypto.SupportedHashes.sha3_256
secp256k1 = crypto.SupportedEncryption.secp256k1


# Don't edit these existing strings or the tests will break
def make_tx():
    return transaction_model.TransactionModel(
        dc_id="something", block_id="an id", txn_id="blah", txn_type="a type", tag="tags", timestamp="123", payload="a payload"
    )


# Don't edit these existing strings or the tests will break
def make_l1_block():
    return l1_block_model.L1BlockModel(
        dc_id="an id",
        block_id="this block num",
        timestamp="129874",
        prev_id="previous block",
        prev_proof="the previous block proof",
        stripped_transactions=["some", "transactions", "which", "are", "strings"],
    )


# Don't edit these existing strings or the tests will break
def make_l2_block():
    return l2_block_model.L2BlockModel(
        dc_id="an id",
        block_id="this block num",
        timestamp="129874",
        prev_proof="the previous block proof",
        l1_block_id="l1 block id",
        l1_dc_id="l1 dc id",
        l1_proof="l1 block proof",
        validations_str='{"a transaction id": true, "another txn id": false}',
    )


# Don't edit these existing strings or the tests will break
def make_l3_block():
    return l3_block_model.L3BlockModel(
        dc_id="an id",
        block_id="this block num",
        timestamp="129874",
        prev_proof="the previous block proof",
        l1_dc_id="l1 dc id",
        l1_block_id="l1 block id",
        l1_proof="l1 block proof",
        ddss="23452",
        l2_count="4",
        regions=["us-west-2"],
        clouds=["aws", "azure"],
    )


# Don't edit these existing strings or the tests will break
def make_l3_block_v2():
    return l3_block_model.L3BlockModel(
        dc_id="an id",
        block_id="this block num",
        timestamp="129874",
        prev_proof="the previous block proof",
        l1_dc_id="l1 dc id",
        l1_block_id="l1 block id",
        l1_proof="l1 block proof",
        l2_proofs=[{"dc_id": "banana", "block_id": "4", "proof": "bananaproof"}],
        ddss="23452",
        l2_count="4",
        regions=["us-west-2"],
        clouds=["aws", "azure"],
    )


def make_l4_block():
    return l4_block_model.L4BlockModel(
        dc_id="an id",
        block_id="this block num",
        timestamp="129874",
        prev_proof="the previous block proof",
        l1_dc_id="l1 dc id",
        l1_block_id="l1 block id",
        l1_proof="l1 block proof",
        validations=[{"l3_dc_id": "l3 dc id", "l3_block_id": "l3 block id", "l3_proof": "l3 block proof", "valid": True}],
    )


def make_l5_block():
    return l5_block_model.L5BlockModel(
        dc_id="an id",
        block_id="this block num",
        timestamp="129874",
        prev_proof="the previous block proof",
        scheme="trust",
        proof="",
        transaction_hash="l1 block hash",
        l4_blocks=[
            '{"dc_id": "40f2ed05-16c8-4c54-9b75-e6f966a54acd","level": 4,"block_id": "77","timestamp": "1537992634","l1_dc_id": "f671b509-042b-4b0d-94f3-247dd1ba2f23","l1_block_id": "21115198","l1_proof": "MEUCIQCAM+HPylScWKYUchsVi6REVGJlJHTefHi7Mx/ZCik1jwIgO1tS7E8AIjL5YZwGVOkJp5r/hUgXRVAIH3GLsHGF8yM=","prev_proof": "MEQCIB5nGgvXzUlV8ff5MVJbcrFSRp4pCGyzt6sy2Rg7moNqAiB98zk5M3dOvi6zT+VqQFkhzKuEN3Ejd/4CgLHCr81DEQ==","l3-validations":[{"l3_dc_id": "1cce7bf3-57f9-46a8-82ed-d39ee51d8d7d","l3_block_id": "107","l3_proof": "APBBxCtc6oEP4EoJLNWnVep0JCQysESrKMu1/w81pxk=","valid": True}],"proof": {"scheme": "trust","proof": "MEUCIQCHTchxcR6Cj9gNFtvgAgiwkZoF88mKFEdpc4U2MnhhtQIgQc76gOlZOfy5e5QXPM+6w2UGCqqLjpoYLyq7GUG6N88="}}'  # noqa: B950
        ],
    )


class TestCrypto(unittest.TestCase):
    def test_tx_blake2b_hashing(self):
        tx = make_tx()
        full_hash, signature = crypto.sign_transaction(blake2b, secp256k1, key, tx)
        self.assertEqual(full_hash, "5z25UmHrb61hA7GFHRN9p28sS/v8H0Tnnb1Bfo4XIuc=")
        tx.invoker = "some invocation id"
        full_hash, signature = crypto.sign_transaction(blake2b, secp256k1, key, tx)
        self.assertEqual(full_hash, "+apS5zAuLgvxGBBwKDHGh8dt/AGVpwSbFmzp7/g8mYE=")

    def test_tx_sha256_hashing(self):
        tx = make_tx()
        full_hash, signature = crypto.sign_transaction(sha256, secp256k1, key, tx)
        self.assertEqual(full_hash, "tvP0nnwld0Ow6Wyvz0T9pS7kQ6qncBo2fBWFDwo9+8I=")
        tx.invoker = "some invocation id"
        full_hash, signature = crypto.sign_transaction(sha256, secp256k1, key, tx)
        self.assertEqual(full_hash, "sYC/PwscI0vKMBlfue/S3saeRVnggkj4XrTeJNwMtmw=")

    def test_tx_sha3_256_hashing(self):
        tx = make_tx()
        full_hash, signature = crypto.sign_transaction(sha3_256, secp256k1, key, tx)
        self.assertEqual(full_hash, "YOuqbUaJYcy6aDrUJVkhZNQjGMZYIU7XtWPxssz4ODA=")
        tx.invoker = "some invocation id"
        full_hash, signature = crypto.sign_transaction(sha3_256, secp256k1, key, tx)
        self.assertEqual(full_hash, "HlYdM5TLQU6xR4lWI0zq0C58vQ9aXdd1va7pYIfwoqo=")

    def test_tx_secp256k1_signing(self):
        tx = make_tx()
        full_hash, signature = crypto.sign_transaction(blake2b, secp256k1, key, tx)
        self.assertEqual(signature, "MEUCIQCsA7IbQ6sIxi6ANJqMEze9eNSFfp8YmPdj8oVnBBy40QIgW30dhhjyZi2WKKdKZoEph844IW3Dfm8sPMoowNrkAhE=")
        tx.invoker = "some invocation id"
        full_hash, signature = crypto.sign_transaction(blake2b, secp256k1, key, tx)
        self.assertEqual(signature, "MEQCIAOavhcfdISa+QD6KkPljl9mnVCneEeFkYCcY8dRlMUYAiBOpm490EX+D7HxHtawCX8sc0+F5N7ofLgcn8lfieyJ7Q==")

    def test_l1block_signing_hashing(self):
        block = make_l1_block()
        sig = crypto.sign_l1_block(blake2b, secp256k1, key, block)
        self.assertEqual(sig, "MEQCIANPrIKBbEmSzM1A/wawqxpKbudPDqiNSg4YXNON/U+lAiBLnAE96DZGvn7YuWAgPQ6V7lLQ1mELtM0/roPq9Ewe0Q==")
        sig = crypto.sign_l1_block(sha256, secp256k1, key, block)
        self.assertEqual(sig, "MEQCICrAJdSIHUuW9LpJvhPiU8GhcMiYpVbUZP6H1VxdsyYhAiBvsGmcHDAaHV+X3NqnZc9efy5BjG2mUDLtEk72SU3NJw==")
        sig = crypto.sign_l1_block(sha3_256, secp256k1, key, block)
        self.assertEqual(sig, "MEQCIHOJwsIyvPQFXn3Dh10bbFSMwRvP9Tyz/wGd/4IW1FD2AiBOmIsOSES4imXd3HGEgU8fG1LdwC3VFoe+HNSqWYbntg==")
        block_hash, nonce = crypto.pow_l1_block(blake2b, block)
        self.assertEqual(block_hash, "AMeMhL0xZOO/FMAPi/Wewa3XxUFPkUAa3gSXz9/6jkk=")
        self.assertEqual(nonce, 206)
        block_hash, nonce = crypto.pow_l1_block(sha256, block)
        self.assertEqual(block_hash, "AAMMEMgqNgT3MJQPpFfzByjCr1qSXzc3NV12DMKzIj0=")
        self.assertEqual(nonce, 252)
        block_hash, nonce = crypto.pow_l1_block(sha3_256, block)
        self.assertEqual(block_hash, "ACvwUNe8DCCiGrulYaN0Tzl3G3eDxB8mTE/XHzf8PCI=")
        self.assertEqual(nonce, 101)

    def test_l2block_signing_hashing(self):
        block = make_l2_block()
        sig = crypto.sign_l2_block(blake2b, secp256k1, key, block)
        self.assertEqual(sig, "MEUCIQDMNOdnmoCmafIAd7XSV3YRpHcNIFZdPKbRrbfco60iNAIgJy9LhlHKPpIf09AaLqsOTyFXGwCWK6CKMKBgoHP+l+M=")
        sig = crypto.sign_l2_block(sha256, secp256k1, key, block)
        self.assertEqual(sig, "MEQCIAnkjRMpeY6dlVTbEb42vipclk9iBSoQl0iOipZ3drTbAiBDd79HBwvU9gumZJ+klY+oPWHzmzBpR1eHEaxdltuF7Q==")
        sig = crypto.sign_l2_block(sha3_256, secp256k1, key, block)
        self.assertEqual(sig, "MEQCICLNLToek+dsToJLT4KYncnLbNe5W5jqkOMfasZbCtU/AiAazSE8BrH1JXEAlChKR7Y13Wab0esLZqTglNCxX+2x2g==")
        block_hash, nonce = crypto.pow_l2_block(blake2b, block)
        self.assertEqual(block_hash, "AOThppUjA/6oKpVCOTWGbbKRn7BPBCEObCuSRSZBAUI=")
        self.assertEqual(nonce, 31)
        block_hash, nonce = crypto.pow_l2_block(sha256, block)
        self.assertEqual(block_hash, "AK8AcqXDgmhp3GznRI22qdwKNbaREr4vfkyqmEriHtI=")
        self.assertEqual(nonce, 402)
        block_hash, nonce = crypto.pow_l2_block(sha3_256, block)
        self.assertEqual(block_hash, "AD2EcFe81+knfu5cuMeDpmVQqndiyxJkJu71xbpP774=")
        self.assertEqual(nonce, 481)

    def test_l3block_signing_hashing(self):
        block = make_l3_block()
        sig = crypto.sign_l3_block(blake2b, secp256k1, key, block)
        self.assertEqual(sig, "MEUCIQCyHIPMVW2P95UVg2qwB3cUJ/PLCij6Xt/A+kChxHkvLgIgbaEeKoh+Xk6cw7i57zewA7Cds/pqQ9pI0x0wxdLeT0g=")
        sig = crypto.sign_l3_block(sha256, secp256k1, key, block)
        self.assertEqual(sig, "MEUCIQDkT3tJDOdRRnBVU1OBDzyWTCufpgWxycASU7R1j17/GAIgKUv2WwR7UBCuM+UVCjKD0hJejifimsfVU8t64ANo/sE=")
        sig = crypto.sign_l3_block(sha3_256, secp256k1, key, block)
        self.assertEqual(sig, "MEQCIDJ1iT2oxbmtoCkfWiHfOKGMwbNBCnx9/ZU/kCL9dZaIAiAhLDMFQWD5ZHBL6tLfdI2vpXj3ABNh50Y+VsGtfYm+RA==")
        block_hash, nonce = crypto.pow_l3_block(blake2b, block)
        self.assertEqual(block_hash, "AHad/NVsJQG7ylDx0PvSrjZCJF6q23VorbQs6wfd2H8=")
        self.assertEqual(nonce, 209)
        block_hash, nonce = crypto.pow_l3_block(sha256, block)
        self.assertEqual(block_hash, "AKMbyq2lS+wgpltP8M8iNe5H2HDE3dpFIdNi0utKp4c=")
        self.assertEqual(nonce, 304)
        block_hash, nonce = crypto.pow_l3_block(sha3_256, block)
        self.assertEqual(block_hash, "ALRr6kQ9RHuL03wcKixF5I/CmG01e9NboWFBNmCpIkE=")
        self.assertEqual(nonce, 289)

    def test_l3block_signing_hashing_v2(self):
        block = make_l3_block_v2()
        sig = crypto.sign_l3_block(blake2b, secp256k1, key, block)
        self.assertEqual(sig, "MEUCIQCqGFxFbx6GgJyKD5AnoP3jVvltyf0bLKfvahLZAfAP2gIgA+b4MbCidhYqeOCoFXw/6lpmC0HNVBc/92xFkZ34J30=")
        sig = crypto.sign_l3_block(sha256, secp256k1, key, block)
        self.assertEqual(sig, "MEQCIDlNXYpyn/1e4ipyesknsWzOSpSalux4PKNFEghabUB9AiAHiQtAycgL1zPtEnxeBZvNeyQ8t9+zOT0hZ5nwxBx5Zg==")
        sig = crypto.sign_l3_block(sha3_256, secp256k1, key, block)
        self.assertEqual(sig, "MEQCIDXuHEv4nshrdv2VgfZmERAqxtL05C8GjtKHHyV4f7UaAiAtCRPQpbjZM3ytcHZbJ4mDtWKu6JokHbFUtBj7aitCeA==")
        block_hash, nonce = crypto.pow_l3_block(blake2b, block)
        self.assertEqual(block_hash, "AGyJopz+O3UboJc5ihiyMkMl8xpSVzvJZ6CQ/RMR0Ec=")
        self.assertEqual(nonce, 533)
        block_hash, nonce = crypto.pow_l3_block(sha256, block)
        self.assertEqual(block_hash, "ADgZ5B9HGoLqwk8FVjNGgHNYHSWOVMFFyjuA6ucYNuM=")
        self.assertEqual(nonce, 27)
        block_hash, nonce = crypto.pow_l3_block(sha3_256, block)
        self.assertEqual(block_hash, "AOicqIqzQZyzrHH1jHW68aFvH+/GUmK3ZcgtD1lt7D0=")
        self.assertEqual(nonce, 312)

    def test_l4block_signing_hashing(self):
        block = make_l4_block()
        sig = crypto.sign_l4_block(blake2b, secp256k1, key, block)
        self.assertEqual(sig, "MEUCIQDpQywi4716Z2ne3lugHeUQK1bncwKq4FGz0JG12B0VNQIgZfNmC2wEkv49jQS+V2w9EtkW7gKpZ2UemjZcvpS5e7E=")
        sig = crypto.sign_l4_block(sha256, secp256k1, key, block)
        self.assertEqual(sig, "MEQCIF6QDgAdvMXzYKUBHKYGUCi3xMFSkKUvJ+97eAF+oSVYAiA6uDJCNl5unULNCsnjonwdNsIdINAS1jISU0IVXzX7qQ==")
        sig = crypto.sign_l4_block(sha3_256, secp256k1, key, block)
        self.assertEqual(sig, "MEQCIFKiiz9V2pGLmPt4XvesVVOATT7cDsPPX6R/h+KmvjSwAiBHBXHkzwhuZKi495n9NnKZg5aEISxXD9luCZukK3V/WA==")
        block_hash, nonce = crypto.pow_l4_block(blake2b, block)
        self.assertEqual(block_hash, "AKF0SMg7YvqBTDJ8cfdk1rNYX0Qt1xKRwRy747yY3VI=")
        self.assertEqual(nonce, 236)
        block_hash, nonce = crypto.pow_l4_block(sha256, block)
        self.assertEqual(block_hash, "AArZIT71V/7OoZuS+yW796R74HMp8Lt/TQvT+3qfD9s=")
        self.assertEqual(nonce, 403)
        block_hash, nonce = crypto.pow_l4_block(sha3_256, block)
        self.assertEqual(block_hash, "AAxZuvIcWV4CeY7pFvCDAUfwNufRNAvUjRk6QIOcYDY=")
        self.assertEqual(nonce, 293)

    def test_l5block_signing_hashing(self):
        block = make_l5_block()
        sig = crypto.sign_l5_block(blake2b, secp256k1, key, block)
        self.assertEqual(sig, "MEUCIQDFki7oqykMTkmm9atTnODzRgDc9hN0zcUB/+Lw44ZHZgIgcC8On8cI59x04y4QE1zwD/duYOZHwWg2b4NCuTXZ9so=")
        sig = crypto.sign_l5_block(sha256, secp256k1, key, block)
        self.assertEqual(sig, "MEQCIF2e1n2ycFUXld5PHxuQreEGnWmg0d56i1stJoH+rdQPAiAFg14QLERoj6apHIqn0ujt+EfxlzeLn5wjjJwGjY8MbQ==")
        sig = crypto.sign_l5_block(sha3_256, secp256k1, key, block)
        self.assertEqual(sig, "MEUCIQDLawvlEFJaYhy/b7xro3L5Y4BBDoHSXgcZdn2GJSj3YgIgPWdEWZiAoE8/MvolN4kpogkxMDTP581tG1A8V1spneg=")

    def test_pow_complexity(self):
        # With base64, each character is 6 bits, and A represents '000000' in binary
        # So we use that to check if our PoW complexity are valid
        block = make_l2_block()
        block_hash, _ = crypto.pow_l2_block(blake2b, block, complexity=6)
        self.assertEqual(block_hash[0], "A")
        block_hash, _ = crypto.pow_l2_block(blake2b, block, complexity=12)
        self.assertEqual(block_hash[0], "A")
        self.assertEqual(block_hash[1], "A")
        block_hash, _ = crypto.pow_l2_block(sha256, block, complexity=6)
        self.assertEqual(block_hash[0], "A")
        block_hash, _ = crypto.pow_l2_block(sha256, block, complexity=12)
        self.assertEqual(block_hash[0], "A")
        self.assertEqual(block_hash[1], "A")
        block_hash, _ = crypto.pow_l2_block(sha3_256, block, complexity=6)
        self.assertEqual(block_hash[0], "A")
        block_hash, _ = crypto.pow_l2_block(sha3_256, block, complexity=12)
        self.assertEqual(block_hash[0], "A")
        self.assertEqual(block_hash[1], "A")

    def test_stripped_tx_verifying(self):
        tx = make_tx()
        full_hash, signature = crypto.sign_transaction(blake2b, secp256k1, key, tx)
        tx.signature = signature
        tx.full_hash = full_hash
        self.assertTrue(crypto.verify_stripped_transaction(blake2b, secp256k1, key.pubkey, tx))
        valid_tx = copy.deepcopy(tx)
        tx.invoker = "forged"
        self.assertFalse(crypto.verify_stripped_transaction(blake2b, secp256k1, key.pubkey, tx))
        tx = copy.deepcopy(valid_tx)
        tx.txn_id = "forged"
        self.assertFalse(crypto.verify_stripped_transaction(blake2b, secp256k1, key.pubkey, tx))
        tx = copy.deepcopy(valid_tx)
        tx.txn_type = "forged"
        self.assertFalse(crypto.verify_stripped_transaction(blake2b, secp256k1, key.pubkey, tx))
        tx = copy.deepcopy(valid_tx)
        tx.timestamp = "forged"
        self.assertFalse(crypto.verify_stripped_transaction(blake2b, secp256k1, key.pubkey, tx))
        tx = copy.deepcopy(valid_tx)
        tx.dc_id = "forged"
        self.assertFalse(crypto.verify_stripped_transaction(blake2b, secp256k1, key.pubkey, tx))
        tx = copy.deepcopy(valid_tx)
        tx.block_id = "forged"
        self.assertFalse(crypto.verify_stripped_transaction(blake2b, secp256k1, key.pubkey, tx))
        tx = copy.deepcopy(valid_tx)
        tx.tag = "forged"
        self.assertFalse(crypto.verify_stripped_transaction(blake2b, secp256k1, key.pubkey, tx))
        tx = copy.deepcopy(valid_tx)
        tx.full_hash = "forged=="
        self.assertFalse(crypto.verify_stripped_transaction(blake2b, secp256k1, key.pubkey, tx))

    def test_full_tx_verifying(self):
        tx = make_tx()
        tx.invoker = "something"
        full_hash, signature = crypto.sign_transaction(blake2b, secp256k1, key, tx)
        tx.signature = signature
        tx.full_hash = full_hash
        self.assertTrue(crypto.verify_full_transaction(blake2b, secp256k1, key.pubkey, tx))
        valid_tx = copy.deepcopy(tx)
        tx.payload = "forged"
        self.assertFalse(crypto.verify_full_transaction(blake2b, secp256k1, key.pubkey, tx))
        tx = copy.deepcopy(valid_tx)
        tx.invoker = "forged"
        self.assertFalse(crypto.verify_full_transaction(blake2b, secp256k1, key.pubkey, tx))
        tx = copy.deepcopy(valid_tx)
        tx.signature = "MEQCIF+o3DHBiTbpw8X6W4/yOuPF/FfANIiNnG0mFLgjBAjuAiAe/QAHN8ufmHMeRvHFItdrzVHFORGED4/msipzFORGED=="
        self.assertFalse(crypto.verify_full_transaction(blake2b, secp256k1, key.pubkey, tx))

    def test_l1block_trust_verifying(self):
        block = make_l1_block()
        sig = crypto.sign_l1_block(blake2b, secp256k1, key, block)
        block.proof = sig
        block.scheme = "trust"
        self.assertTrue(crypto.verify_l1_block_trust(blake2b, secp256k1, key.pubkey, block))
        valid_block = copy.deepcopy(block)
        block.dc_id = "forged"
        self.assertFalse(crypto.verify_l1_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.block_id = "forged"
        self.assertFalse(crypto.verify_l1_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.timestamp = "forged"
        self.assertFalse(crypto.verify_l1_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.prev_id = "forged"
        self.assertFalse(crypto.verify_l1_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.prev_proof = "forged=="
        self.assertFalse(crypto.verify_l1_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.stripped_transactions = ["some", "forged", "txns"]
        self.assertFalse(crypto.verify_l1_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.proof = "MEQCIF+o3DHBiTbpw8X6W4/yOuPF/FfANIiNnG0mFLgjBAjuAiAe/QAHN8ufmHMeRvHFItdrzVHFORGED4/msipzFORGED=="
        self.assertFalse(crypto.verify_l1_block_trust(blake2b, secp256k1, key.pubkey, block))

    def test_l2block_trust_verifying(self):
        block = make_l2_block()
        sig = crypto.sign_l2_block(blake2b, secp256k1, key, block)
        block.proof = sig
        block.scheme = "trust"
        self.assertTrue(crypto.verify_l2_block_trust(blake2b, secp256k1, key.pubkey, block))
        valid_block = copy.deepcopy(block)
        block.dc_id = "forged"
        self.assertFalse(crypto.verify_l2_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.block_id = "forged"
        self.assertFalse(crypto.verify_l2_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.timestamp = "forged"
        self.assertFalse(crypto.verify_l2_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.prev_proof = "forged=="
        self.assertFalse(crypto.verify_l2_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.validations_str = '{"forged": true}'
        self.assertFalse(crypto.verify_l2_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.l1_dc_id = "forged"
        self.assertFalse(crypto.verify_l2_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.l1_block_id = "forged"
        self.assertFalse(crypto.verify_l2_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.l1_proof = "forged"
        self.assertFalse(crypto.verify_l2_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.proof = "MEQCIF+o3DHBiTbpw8X6W4/yOuPF/FfANIiNnG0mFLgjBAjuAiAe/QAHN8ufmHMeRvHFItdrzVHFORGED4/msipzFORGED=="
        self.assertFalse(crypto.verify_l2_block_trust(blake2b, secp256k1, key.pubkey, block))

    def test_l3block_trust_verifying(self):
        block = make_l3_block()
        sig = crypto.sign_l3_block(blake2b, secp256k1, key, block)
        block.proof = sig
        block.scheme = "trust"
        self.assertTrue(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        valid_block = copy.deepcopy(block)
        block.dc_id = "forged"
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.block_id = "forged"
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.timestamp = "forged"
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.prev_proof = "forged=="
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.l1_dc_id = "forged"
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.l1_block_id = "forged"
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.l1_proof = "forged"
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.ddss = "forged"
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.l2_count = "forged"
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.regions = ["forged", "stuff"]
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.clouds = ["forged"]
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.proof = "MEQCIF+o3DHBiTbpw8X6W4/yOuPF/FfANIiNnG0mFLgjBAjuAiAe/QAHN8ufmHMeRvHFItdrzVHFORGED4/msipzFORGED=="
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))

    def test_l3block_trust_verifying_v2(self):
        block = make_l3_block_v2()
        sig = crypto.sign_l3_block(blake2b, secp256k1, key, block)
        block.proof = sig
        block.scheme = "trust"
        self.assertTrue(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        valid_block = copy.deepcopy(block)
        block.dc_id = "forged"
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.block_id = "forged"
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.timestamp = "forged"
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.prev_proof = "forged=="
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.l1_dc_id = "forged"
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.l1_block_id = "forged"
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.l1_proof = "forged"
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.ddss = "forged"
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.l2_count = "forged"
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.regions = ["forged", "stuff"]
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.clouds = ["forged"]
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.proof = "MEQCIF+o3DHBiTbpw8X6W4/yOuPF/FfANIiNnG0mFLgjBAjuAiAe/QAHN8ufmHMeRvHFItdrzVHFORGED4/msipzFORGED=="
        self.assertFalse(crypto.verify_l3_block_trust(blake2b, secp256k1, key.pubkey, block))

    def test_l4block_trust_verifying(self):
        block = make_l4_block()
        sig = crypto.sign_l4_block(blake2b, secp256k1, key, block)
        block.proof = sig
        block.scheme = "trust"
        self.assertTrue(crypto.verify_l4_block_trust(blake2b, secp256k1, key.pubkey, block))
        valid_block = copy.deepcopy(block)
        block.dc_id = "forged"
        self.assertFalse(crypto.verify_l4_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.block_id = "forged"
        self.assertFalse(crypto.verify_l4_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.timestamp = "forged"
        self.assertFalse(crypto.verify_l4_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.prev_proof = "forged=="
        self.assertFalse(crypto.verify_l4_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.l1_dc_id = "forged"
        self.assertFalse(crypto.verify_l4_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.l1_block_id = "forged"
        self.assertFalse(crypto.verify_l4_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.l1_proof = "forged"
        self.assertFalse(crypto.verify_l4_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.validations[0]["l3_dc_id"] = "forged"
        self.assertFalse(crypto.verify_l4_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.validations[0]["l3_block_id"] = "forged"
        self.assertFalse(crypto.verify_l4_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.validations[0]["l3_proof"] = "forged"
        self.assertFalse(crypto.verify_l4_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.validations[0]["valid"] = False
        self.assertFalse(crypto.verify_l4_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.proof = "MEQCIF+o3DHBiTbpw8X6W4/yOuPF/FfANIiNnG0mFLgjBAjuAiAe/QAHN8ufmHMeRvHFItdrzVHFORGED4/msipzFORGED=="
        self.assertFalse(crypto.verify_l4_block_trust(blake2b, secp256k1, key.pubkey, block))

    def test_l5block_trust_verifying(self):
        block = make_l5_block()
        sig = crypto.sign_l5_block(blake2b, secp256k1, key, block)
        block.proof = sig
        block.scheme = "trust"
        self.assertTrue(crypto.verify_l5_block_trust(blake2b, secp256k1, key.pubkey, block))
        valid_block = copy.deepcopy(block)
        block.dc_id = "forged"
        self.assertFalse(crypto.verify_l5_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.block_id = "forged"
        self.assertFalse(crypto.verify_l5_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.timestamp = "forged"
        self.assertFalse(crypto.verify_l5_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.prev_proof = "forged=="
        self.assertFalse(crypto.verify_l5_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.l4_blocks[0] = "forged"
        self.assertFalse(crypto.verify_l5_block_trust(blake2b, secp256k1, key.pubkey, block))
        block = copy.deepcopy(valid_block)
        block.proof = "MEQCIF+o3DHBiTbpw8X6W4/yOuPF/FfANIiNnG0mFLgjBAjuAiAe/QAHN8ufmHMeRvHFItdrzVHFORGED4/msipzFORGED=="
        self.assertFalse(crypto.verify_l5_block_trust(blake2b, secp256k1, key.pubkey, block))

    def test_l1block_pow_verifying(self):
        block = make_l1_block()
        block_hash, nonce = crypto.pow_l1_block(blake2b, block)
        block.proof = block_hash
        block.nonce = nonce
        block.scheme = "work"
        self.assertTrue(crypto.verify_l1_block_pow(blake2b, block))
        valid_block = copy.deepcopy(block)
        block.dc_id = "forged"
        self.assertFalse(crypto.verify_l1_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.block_id = "forged"
        self.assertFalse(crypto.verify_l1_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.timestamp = "forged"
        self.assertFalse(crypto.verify_l1_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.prev_id = "forged"
        self.assertFalse(crypto.verify_l1_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.prev_proof = "forged=="
        self.assertFalse(crypto.verify_l1_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.stripped_transactions = ["some", "forged", "txns"]
        self.assertFalse(crypto.verify_l1_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.proof = "47DEQpj8HBSa+/FORGEDJCeuQeRkm5NMpJWZG3hSuFU="
        self.assertFalse(crypto.verify_l1_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.nonce = 0
        self.assertFalse(crypto.verify_l1_block_pow(blake2b, block))

    def test_l2block_pow_verifying(self):
        block = make_l2_block()
        block_hash, nonce = crypto.pow_l2_block(blake2b, block)
        block.proof = block_hash
        block.nonce = nonce
        block.scheme = "work"
        self.assertTrue(crypto.verify_l2_block_pow(blake2b, block))
        valid_block = copy.deepcopy(block)
        block.dc_id = "forged"
        self.assertFalse(crypto.verify_l2_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.block_id = "forged"
        self.assertFalse(crypto.verify_l2_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.timestamp = "forged"
        self.assertFalse(crypto.verify_l2_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.prev_proof = "forged=="
        self.assertFalse(crypto.verify_l2_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.validations_str = '{"forged": true}'
        self.assertFalse(crypto.verify_l2_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.l1_dc_id = "forged"
        self.assertFalse(crypto.verify_l2_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.l1_block_id = "forged"
        self.assertFalse(crypto.verify_l2_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.l1_proof = "forged"
        self.assertFalse(crypto.verify_l2_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.proof = "47DEQpj8HBSa+/FORGEDJCeuQeRkm5NMpJWZG3hSuFU="
        self.assertFalse(crypto.verify_l2_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.nonce = 0
        self.assertFalse(crypto.verify_l2_block_pow(blake2b, block))

    def test_l3block_pow_verifying(self):
        block = make_l3_block()
        block_hash, nonce = crypto.pow_l3_block(blake2b, block)
        block.proof = block_hash
        block.nonce = nonce
        block.scheme = "work"
        self.assertTrue(crypto.verify_l3_block_pow(blake2b, block))
        valid_block = copy.deepcopy(block)
        block.dc_id = "forged"
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.block_id = "forged"
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.timestamp = "forged"
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.prev_proof = "forged=="
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.l1_dc_id = "forged"
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.l1_block_id = "forged"
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.l1_proof = "forged"
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.ddss = "forged"
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.l2_count = "forged"
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.regions = ["forged", "stuff"]
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.clouds = ["forged"]
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.proof = "47DEQpj8HBSa+/FORGEDJCeuQeRkm5NMpJWZG3hSuFU="
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.nonce = 0
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))

    def test_l3block_pow_verifying_v2(self):
        block = make_l3_block_v2()
        block_hash, nonce = crypto.pow_l3_block(blake2b, block)
        block.proof = block_hash
        block.nonce = nonce
        block.scheme = "work"
        self.assertTrue(crypto.verify_l3_block_pow(blake2b, block))
        valid_block = copy.deepcopy(block)
        block.dc_id = "forged"
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.block_id = "forged"
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.timestamp = "forged"
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.prev_proof = "forged=="
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.l1_dc_id = "forged"
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.l1_block_id = "forged"
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.l1_proof = "forged"
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.ddss = "forged"
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.l2_count = "forged"
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.regions = ["forged", "stuff"]
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.clouds = ["forged"]
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.proof = "47DEQpj8HBSa+/FORGEDJCeuQeRkm5NMpJWZG3hSuFU="
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.nonce = 0
        self.assertFalse(crypto.verify_l3_block_pow(blake2b, block))

    def test_l4block_pow_verifying(self):
        block = make_l4_block()
        block_hash, nonce = crypto.pow_l4_block(blake2b, block)
        block.proof = block_hash
        block.nonce = nonce
        block.scheme = "work"
        self.assertTrue(crypto.verify_l4_block_pow(blake2b, block))
        valid_block = copy.deepcopy(block)
        block.dc_id = "forged"
        self.assertFalse(crypto.verify_l4_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.block_id = "forged"
        self.assertFalse(crypto.verify_l4_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.timestamp = "forged"
        self.assertFalse(crypto.verify_l4_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.prev_proof = "forged=="
        self.assertFalse(crypto.verify_l4_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.l1_dc_id = "forged"
        self.assertFalse(crypto.verify_l4_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.l1_block_id = "forged"
        self.assertFalse(crypto.verify_l4_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.l1_proof = "forged"
        self.assertFalse(crypto.verify_l4_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.validations[0]["l3_dc_id"] = "forged"
        self.assertFalse(crypto.verify_l4_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.validations[0]["l3_block_id"] = "forged"
        self.assertFalse(crypto.verify_l4_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.validations[0]["l3_proof"] = "forged"
        self.assertFalse(crypto.verify_l4_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.validations[0]["valid"] = False
        self.assertFalse(crypto.verify_l4_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.proof = "47DEQpj8HBSa+/FORGEDJCeuQeRkm5NMpJWZG3hSuFU="
        self.assertFalse(crypto.verify_l4_block_pow(blake2b, block))
        block = copy.deepcopy(valid_block)
        block.nonce = 0
        self.assertFalse(crypto.verify_l4_block_pow(blake2b, block))

    def test_hash_bytes(self):
        self.assertEqual(
            crypto.hash_bytes(sha256, b"some data"), b"\x13\x07\x99\x0ek\xa5\xca\x14^\xb3^\x99\x18*\x9b\xecFS\x1b\xc5M\xdfej`,x\x0f\xa0$\r\xee"
        )
        self.assertEqual(
            crypto.hash_bytes(sha3_256, b"some data"), b"Y3\xe9'1f\x93Jn\xba\xafX\x17\x10tG\x93\t\xa7\xde\x84`|E\x0b\x01\xc2e\xb3\x08\x17\x12"
        )
        self.assertEqual(
            crypto.hash_bytes(blake2b, b"some data"), b"\x10\x1e\x81\x93\x91x\xf8Jn\x89o\xe1\xc2c\x8fo\x9e\x16q\x1d\x94,N\xfe\xc6\xf2\x8du\x19\xc1{W"
        )

    def test_create_public_id(self):
        self.assertEqual(crypto.calculate_public_id(key.pubkey.serialize()), "kMJK6Ywugvu8qVaPgnoxHV9Be1QvxNyF2CPdc42WmajC")

    def test_validate_public_id(self):
        self.assertTrue(crypto.validate_public_id(key.pubkey.serialize(), "kMJK6Ywugvu8qVaPgnoxHV9Be1QvxNyF2CPdc42WmajC"))
        self.assertFalse(crypto.validate_public_id(key.pubkey.serialize(), "PHONYtbS59pt3weCTD8fw3WP5zA3DieeM2j6mC3fzaZa"))

    def test_hmac(self):
        secret = "12345"
        message = "POST\n/chains/transaction\nbanana-uuid\napplication/json\nfh8uIpSrKpzoYwrjaVtnduas5M34B4ZPrX+jTNjP6/o=\n1537305660"
        hmac = crypto.create_hmac(blake2b, secret, message)
        self.assertTrue(crypto.compare_hmac(blake2b, hmac, secret, message))
        self.assertEqual(
            hmac,
            b'\xa3\x99\x9c\xd1\x99}_\xb2\xf8\xad\xb7\x88i\x87\xe6\xea\xec\x93`\xcd\xa1\xb1v\xcf\xaf\x7f\xdb+?\xbfk=Z$\x17\x1f\xf3r\xab\xc1\x97\xd5\x04;\xd9\x16gZ">j=\n\xf4Dy\xc5b\x9b\x87\xb7\xfc\x9e\xfd',  # noqa B950
        )
        hmac = crypto.create_hmac(sha256, secret, message)
        self.assertTrue(crypto.compare_hmac(sha256, hmac, secret, message))
        self.assertEqual(hmac, b"\xa7{c\x0f\x9b\xfc\xe8\x1b\x88\xd4\x10A\x80U\x07\x16\x18>\xa3\xafz`M\xe0\x05r#\x0b\x81\xb0\xc2\xf1")
        hmac = crypto.create_hmac(sha3_256, secret, message)
        self.assertTrue(crypto.compare_hmac(sha3_256, hmac, secret, message))
        self.assertEqual(hmac, b"i\x9d{!g\x90\xe2\xe6\xeeSd\xefS\xf2\x84\xab\x91\xda\xb7\xa8$\xf8\x91\xe6\x83\xd8+\xf2D\xbd\x9b\x8f")

    def test_generic_signature(self):
        content = "some random stuff to sign as a".encode("utf-8")
        sig = crypto.make_generic_signature(secp256k1, sha256, key, content)
        self.assertTrue(crypto.check_generic_signature(secp256k1, sha256, key.pubkey, content, b64decode(sig)))

    def test_unsupported_crypto(self):
        l1block = make_l1_block()
        l1block.proof = "sig="
        self.assertRaises(NotImplementedError, crypto.create_hmac, 99999, "secret", "message")
        self.assertRaises(NotImplementedError, crypto.verify_l1_block_trust, 99999, secp256k1, key, l1block)
        self.assertRaises(NotImplementedError, crypto.verify_l1_block_trust, blake2b, 99999, key, l1block)
        self.assertRaises(NotImplementedError, crypto.sign_l1_block, blake2b, 99999, key, l1block)

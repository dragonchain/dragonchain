import unittest
from unittest import TestCase

import blockchain.util.crypto as crypto


class TestFinal_hash(unittest.TestCase):
    def test_final_hash(self):
        """  Testing final_hash() with an arbitrary return value of Hello World to verify it is true
             as well as testing that if you give function empty string, it still hashes properly """
        test_val = crypto.final_hash("Hello World")
        self.assertEquals(test_val, "e63006bd9f35f06cd20582fc8b34ae76a15080297be886decd6dfd42f59e5174a537e8cd92ef577297f967beb6b758c1835f4c270c251e10c12331fcd8635c53")
        self.assertFalse(crypto.final_hash("") == "")


class TestBytes2long(unittest.TestCase):
    def test_bytes2long(self):
        self.assertRaises(AttributeError, crypto.bytes2long, 123)
        self.assertRaises(ValueError, crypto.bytes2long, "")

        test_val = crypto.bytes2long("111233345556@")
        self.assertEqual(test_val, 3897404203108157008445053417024)
        self.assertTrue(isinstance(test_val, long))


class TestDeterministicHash(TestCase):
    def test_deterministic_hash(self):
        """ Mock list of prior_block_hash, lower_phase_hash, signatory, signature_ts, public key, block_id, phase,
            verification_ts, deep_hash(verification_info)
        """

        # testing to insure that hashed items may contain a mix of strings, numbers or None types.
        hashed_items = ["123456", "654321", "transaction-service", 1476664195, "xeKuS9t8A=\n-----END PUBLIC KEY-----\n",
                        "8885196", 1, "origin_id", 1476664210, "553412456235", None]

        # calculate hash for hashed_items
        val = crypto.deterministic_hash(hashed_items)

        # insure the returned hash value of hashed_items matches what it should be
        self.assertEqual(val, 233888947446904696754100748358486582297006536790227845537678672765978391714164843162143)

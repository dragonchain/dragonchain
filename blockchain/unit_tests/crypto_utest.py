import unittest
from unittest import TestCase

import blockchain.util.crypto as crypto


class TestFinal_hash(unittest.TestCase):
    def test_final_hash(self):
        pass


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
        hashed_items = ["123456", "654321", "transaction-service", 1476664195, "xeKuS9t8A=\n-----END PUBLIC KEY-----\n",
                        "8885196", 1, "origin_id", 1476664210, "553412456235", None]

        val = crypto.deterministic_hash(hashed_items)
        self.assertEqual(val, 233888947446904696754100748358486582297006536790227845537678672765978391714164843162143)

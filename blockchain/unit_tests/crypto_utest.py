import unittest
import blockchain.util.crypto as crypto


class TestBytes2long(unittest.TestCase):
    def test_bytes2long(self):
        self.assertRaises(AttributeError, crypto.bytes2long, 123)
        self.assertRaises(ValueError, crypto.bytes2long, "")

        test_val = crypto.bytes2long("111233345556@")
        self.assertEqual(crypto.bytes2long("111233345556@"), 3897404203108157008445053417024)
        self.assertTrue(isinstance(test_val, long))

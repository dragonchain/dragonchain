import unittest
import blockchain.util.crypto as crypto


class TestFinal_hash(unittest.TestCase):
    def test_final_hash(self):
        self.assertEquals(crypto.final_hash("1111111111111111"),"31bca02094eb78126a517b206a88c73cfa9ec6f704c7030d18212cace820f025f00bf0ea68dbf3f3a5436ca63b53bf7bf80ad8d5de7d8359d0b7fed9dbc3ab99")
        self.assertFalse(crypto.final_hash("") == "")

class TestBytes2long(unittest.TestCase):
    def test_bytes2long(self):
        self.assertRaises(AttributeError, crypto.bytes2long, 123)
        self.assertRaises(ValueError, crypto.bytes2long, "")

        test_val = crypto.bytes2long("111233345556@")
        self.assertEqual(crypto.bytes2long("111233345556@"), 3897404203108157008445053417024)
        self.assertTrue(isinstance(test_val, long))
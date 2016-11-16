import unittest
import time
from unittest import TestCase

import blockchain.util.crypto as crypto


class TestFinal_hash(unittest.TestCase):
    def test_final_hash(self):
        """  Testing final_hash() with an arbitrary return value of Hello World to verify it is true
             as well as testing that if you give function empty string, it still hashes properly """
        test_val = crypto.final_hash("Hello World")
        self.assertEquals(test_val,
                          "e63006bd9f35f06cd20582fc8b34ae76a15080297be886decd6dfd42f59e5174a537e8cd92ef577297f967beb6b758c1835f4c270c251e10c12331fcd8635c53")
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


class TestSignVerificationRecord(TestCase):
    def test_sign_verification_record(self):
        signatory = "31ce807a-868c-11e6-99f6-3c970e3bee11"
        prior_block_hash = "c26a38fefb2140ac36163b79c31050eaa4021d44fa121e521a43e0283b3fba3cb6f723d57cb9ae4108603942ad38d4ebfd2a0325f6c19e580627e063188a1624"
        lower_phase_hash = 0
        public_key = "-----BEGIN PUBLIC KEY-----\nME4wEAYHKoZIzj0CAQYFK4EEACEDOgAE7pcbDVgIxjjvYS4Ce+cR54vH+mgb5OvK\nwNQfh4iH8GyLjM0LpbZuuKh090/D7jONd+xeKuS9t8A=\n-----END PUBLIC KEY-----"
        private_key = "-----BEGIN EC PARAMETERS-----\nBgUrgQQAIQ==\n-----END EC PARAMETERS-----\n-----BEGIN EC PRIVATE KEY-----\nMGgCAQEEHGLBg95ayw1hDWUMsfTdqnlQmVpz3n1vTzr7yhmgBwYFK4EEACGhPAM6\nAATulxsNWAjGOO9hLgJ75xHni8f6aBvk68rA1B+HiIfwbIuMzQultm64qHT3T8Pu\nM4137F4q5L23wA==\n-----END EC PRIVATE KEY-----"
        block_id = 9404771
        phase = 1
        origin_id = "31ce807a-868c-11e6-99f6-3c970e3bee11"
        verification_ts = int(time.time())
        verification_info = ""

        expected_output = {'phase': 1, 'verification_record': {'verification_info': '', 'verification_ts': 1479266547, 'block_id': 9404771,
                                                               'lower_phase_hash': 0, 'origin_id': '31ce807a-868c-11e6-99f6-3c970e3bee11',
                                                               'signature': {'signatory': '31ce807a-868c-11e6-99f6-3c970e3bee11',
                                                                             'hash': 'f3580fb50cbf07432aa2ed87c6737ab180c3d1d387e09b121aead1d9837'
                                                                                     '5402e9df52febe72c6fced1c59b59dcad41dde729e84962c2480ce4a4ecf9bd073f16',
                                                                             'public_key': '-----BEGIN PUBLIC KEY-----\nME4wEAYHKoZIzj0CAQYFK4EEACEDOgAE7pcbDV'
                                                                                           'gIxjjvYS4Ce+cR54vH+mgb5OvK\nwNQfh4iH8GyLjM0LpbZuuKh090/'
                                                                                           'D7jONd+xeKuS9t8A=\n-----END PUBLIC KEY-----',
                                                                             'signature_ts': 1479266547, 'signature': 'DFuKdobLwr53cg2shQtiGw+W7mK6ikAJ8TtAOj78'
                                                                                                                      'nFUcIbW3TEIn9spiXRH1fDJehGRTfPBCjjs=\n'},
                                                               'phase': 1, 'prior_hash': 'c26a38fefb2140ac36163b79c31050eaa4021d44fa121e521a43e0283b3fba3cb6f72'
                                                                                         '3d57cb9ae4108603942ad38d4ebfd2a0325f6c19e580627e063188a1624'},
                           'block_id': 9404771}

        test_output = crypto.sign_verification_record(signatory, prior_block_hash,lower_phase_hash, public_key,private_key,block_id, phase, origin_id, verification_ts, verification_info)
        self.assertEqual(expected_output['verification_record']['signature']['hash'], test_output['verification_record']['signature']['hash'])


class TestSignTransaction(TestCase):
    def test_sign_transaction(self):
        signatory = "18d956e7-bc61-4f70-8f72-3f0bb25f01a6"

        # simplified private and public keys
        private_key_string = "-----BEGIN EC PARAMETERS-----\nBgUrgQQAIQ==\n-----END EC PARAMETERS-----\n-----BEGIN EC PRIVATE KEY-----\nMGgCAQEEHGLBg95ayw1hDWUMsfTdqnlQmVpz3n1vTzr7yhmgBwYFK4EEACGhPAM6\nAATulxsNWAjGOO9hLgJ75xHni8f6aBvk68rA1B+HiIfwbIuMzQultm64qHT3T8Pu\nM4137F4q5L23wA==\n-----END EC PRIVATE KEY-----"

        public_key_string = "-----BEGIN PUBLIC KEY-----\nME4wEAYHKoZIzj0CAQYFK4EEACEDOgAE7pcbDVgIxjjvYS4Ce+cR54vH+mgb5OvK\nwNQfh4iH8GyLjM0LpbZuuKh090/D7jONd+xeKuS9t8A=\n-----END PUBLIC KEY-----"

        transaction = {'header': {'transaction_id': '8a864b59-46e3-4c9b-8dfd-9d9a2bd4b754',
                                  'transaction_ts': 1479264525,
                                  'actor': 'c26dd972-8683-11e6-977b-3c970e3bee11',
                                  'business_unit': 'a3e13076-8683-11e6-97a9-3c970e3bee11',
                                  'create_ts': 1475180987,
                                  'entity': 'c78f4526-8683-11e6-b1c6-3c970e3bee11',
                                  'family_of_business': 'Test Business Family',
                                  'line_of_business': 'My Business',
                                  'owner': 'Test Node',
                                  'transaction_type': 'TT_REQ'
                                  },
                       'payload': {'action': {'amount': '5.0', 'artifact_id': '12345', 'name': 'Test Payload'},
                                   'source': 'f36c9086-8683-11e6-80dc-3c970e3bee11'}
                       }
        test_transaction = crypto.sign_transaction(signatory, private_key_string, public_key_string, transaction)

        # check if signature made it into transaction
        self.assertEqual('signature' in test_transaction, True)

        test_transaction.pop('header')
        self.assertRaises(KeyError, crypto.sign_transaction, signatory, private_key_string, public_key_string, test_transaction)

import unittest
import base64

from mock import patch

from dragonchain.lib.faas import get_faas_auth


class TestGetFaaSAuth(unittest.TestCase):
    @patch("builtins.open", unittest.mock.mock_open(read_data="mydata"))
    def test_delete_contract(self):
        my_fake_auth = f"Basic {base64.b64encode('mydata:mydata'.encode('utf-8')).decode('ascii')}"
        data = get_faas_auth()
        self.assertEqual(my_fake_auth, data)

# Copyright 2020 Dragonchain, Inc.
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

import os
import unittest
from unittest.mock import patch, mock_open

from dragonchain import test_env  # noqa: F401
from dragonchain import exceptions
from dragonchain.lib.interfaces.local import disk


class TestDiskInterface(unittest.TestCase):
    def test_process_key_replaces_dots(self):
        self.assertEqual(disk.process_key("../key"), "__/key")

    @patch("builtins.open", new_callable=mock_open)
    def test_get_opens_correct_file(self, mock_file):
        path = os.path.join("loc", "key")
        disk.get("loc", "key")
        mock_file.assert_called_once_with(path, "rb")

    @patch("builtins.open", new_callable=mock_open, read_data=b"data")
    def test_get_returns_file_data(self, mock_file):
        self.assertEqual(disk.get("loc", "key"), b"data")

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_get_throws_notfound_on_filenotfound(self, mock_file):
        self.assertRaises(exceptions.NotFound, disk.get, "loc", "key")

    @patch("builtins.open", new_callable=mock_open)
    def test_put_opens_correct_file(self, mock_file):
        path = os.path.join("loc", "key")
        disk.put("loc", "key", b"data")
        mock_file.assert_called_once_with(path, "wb")

    @patch("builtins.open", side_effect=NotADirectoryError)
    @patch("dragonchain.lib.interfaces.local.disk.os.makedirs")
    def test_put_makes_dirs_when_needed(self, mock_make_dirs, mock_file):
        self.assertRaises(NotADirectoryError, disk.put, "loc", "key", b"data")
        mock_make_dirs.assert_called_once_with(os.path.dirname(os.path.join("loc", "key")))

    @patch("dragonchain.lib.interfaces.local.disk.os.remove")
    def test_delete_calls_os_remove_with_correct_params(self, mock_remove):
        disk.delete("loc", "key")
        mock_remove.assert_called_once_with(os.path.join("loc", "key"))

    @patch("dragonchain.lib.interfaces.local.disk.os.rmdir")
    @patch("dragonchain.lib.interfaces.local.disk.os.walk", return_value=[("/path", ("ext",), ()), ("/path/ext", (), ())])
    def test_delete_directory_recursively_deletes(self, mock_walk, mock_rm_dir):
        disk.delete_directory("loc", "dir")
        mock_walk.assert_called_once()
        self.assertEqual(mock_rm_dir.call_count, 2)

    @patch("dragonchain.lib.interfaces.local.disk.get", return_value=b'{"txn_id":"mock","txn":{"da":"ta"}}\n')
    def test_select_transaction_parses_txn_id(self, mock_get):
        self.assertEqual(disk.select_transaction("loc", "block", "mock"), {"da": "ta"})

    @patch("dragonchain.lib.interfaces.local.disk.get", return_value=b'{"txn_id":"mock","txn":{"da":"ta"}}\n')
    def test_select_transaction_returns_not_found(self, mock_get):
        self.assertRaises(exceptions.NotFound, disk.select_transaction, "loc", "block", "bogus")

    @patch("dragonchain.lib.interfaces.local.disk.os.walk", return_value=[("path", ("obj",), ("obj1",)), ("path/obj", (), ("obj2",))])
    def test_list_objects_returns_correct_objects(self, mock_walk):
        self.assertEqual(disk.list_objects("path", "obj"), ["obj1", os.path.join("obj", "obj2")])

    @patch("dragonchain.lib.interfaces.local.disk.os.path.isdir")
    def test_does_superkey_exit_calls_isdir_with_correct_params(self, mock_isdir):
        disk.does_superkey_exist("loc", "thing")
        mock_isdir.assert_called_once_with(os.path.join("loc", "thing"))

    @patch("dragonchain.lib.interfaces.local.disk.os.path.isfile")
    def test_does_object_exit_calls_isfile_with_correct_params(self, mock_isfile):
        disk.does_object_exist("loc", "thing")
        mock_isfile.assert_called_once_with(os.path.join("loc", "thing"))

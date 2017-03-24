"""
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
"""
__author__ = "Steve Owens"
__copyright__ = "Copyright 2017, Disney Connected and Advanced Technologies"
__license__ = "Apache"
__version__ = "2.0"
__maintainer__ = "Steve Owens"
__email__ = "steveo98501@gmail.com"

from blockchain.db.postgres.utilities.sql_clause_builder import SQLClauseBuilder
import unittest

class TestAllStringValues(unittest.TestCase):
    def test_all_string_values(self):
        """ testing all string values """
        builder = SQLClauseBuilder("AND")
        valid_params =  ["foo", "bar", "baz"]
        field_values = {"foo":"gimble", "bar":"bimble", "baz":"grump"}
        test_val = builder.build("string", valid_params, field_values)
        expected_val = '"bar" = \'bimble\' AND "baz" = \'grump\' AND "foo" = \'gimble\''
        self.assertEqual(test_val, expected_val)

    def test_time_ranges(self):
        """ testing all string values """
        builder = SQLClauseBuilder("AND")
        valid_params =  ["epoch_dash", "dash_epoch", 
                         "epoch_dash_epoch", "epoch"]
        field_values = {"epoch_dash": "1490312638-", 
                        "dash_epoch":"-1490312638", 
                        "epoch_dash_epoch":"1490312638-1490112638",
                        "epoch":"1490312638"}
        test_val = builder.build("time_range", valid_params, field_values)
        expected_val = ("\"dash_epoch\" >= '2017-03-23 23:43:58' " + 
            "AND \"epoch\" = '2017-03-23 23:43:58' " +
            "AND \"epoch_dash\" <= '2017-03-23 23:43:58' " + 
            "AND \"epoch_dash_epoch\" >= '2017-03-23 23:43:58' AND " +
            "\"epoch_dash_epoch\" <= '2017-03-21 16:10:38'")
        self.assertEqual(test_val, expected_val)
        
"""
Created on Mar 23, 2017
Copyright 2017 Disney Connected and Advanced Technologies

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
__email__ = "steve098501@gmail.com"

import time

class SQLClauseBuilder(object):
    """
    This module encapsulates the conversion of a set of keyword arguments into a postgresql where clause.
    The intent is to enable the replacement of long chains of code of the form

    if "block_id" in params:
        query += ''' block_id = ''' + str(params['block_id'])
        separator_needed = True

    if "transaction_type" in params:
        if separator_needed:
            query += ''' AND '''
        query += " transaction_type = '" + str(params["transaction_type"]) + "'"
        separator_needed = True
        
        ...
        ...
        
    With a more concise expression
    """
    __valid_types = ["string", "time_range"]
    
    def __init__(self):
        '''
        Constructor takes a joining operator which is an element of
        the set { 'AND', 'OR', ','} and joins the elements of 
        field_values into equality / assignment statements.
        '''
    
    def __assert_valid_param_type(self, param_type):
        if param_type not in self.__valid_types:
            raise ValueError("param_type must be one of [" 
                             + ','.join(self.__valid_types))
        
    def __build_string_segment(self, field_name, field_value):
        """
        """
        return "\"" + field_name + "\" = '" + field_value + "'"
    
    def __build_time_range_segment(self, field_name, field_value):
        """
        """
        if '-' in field_value:
            times = [x for x in field_value.split("-") if x]
            if len(times) == 1:
                # if it is timestamp >= UNIX-epoch timecode
                if field_value.index('-') == 0:
                    start_time = time.strftime(
                                    '%Y-%m-%d %H:%M:%S', 
                                    time.gmtime(float(times[0])))
                    return '"' + field_name + "\" >= '" + start_time + "'"
                elif field_value.endswith('-'):
                    end_time = time.strftime(
                                    '%Y-%m-%d %H:%M:%S',
                                    time.gmtime(float(times[0])))
                    return '"' + field_name + "\" <= '" + end_time + "'"
            elif len(times) == 2:
                start_time = time.strftime(
                                '%Y-%m-%d %H:%M:%S',
                                time.gmtime(float(times[0])))
                end_time = time.strftime(
                                '%Y-%m-%d %H:%M:%S', 
                                time.gmtime(float(times[1])))
                return ('"' +field_name + "\" >= '" + start_time + 
                        "' AND \"" + field_name + "\" <= '" + end_time + "'")
            else:
                raise ValueError("field_value '" + field_value 
                                 + "' has too many '-' characters.")
        else:
            cur_time = time.strftime('%Y-%m-%d %H:%M:%S', 
                                      time.gmtime(float(field_value)))
            return '"' + field_name + "\" = '" + cur_time + "'"
    
    def __build_segment(self, param_type, field_name, field_value):
        """
        Routes the field_name and field_value params to the right segment
        builder for the param_type
        """
        if param_type == "string":
            return self.__build_string_segment(field_name, field_value)
        if param_type == "time_range":
            return self.__build_time_range_segment(field_name, field_value)
        
    def build(self, conjunctive_operator, param_type, valid_params = [], field_values = {}):
        """ 
        Loop through valid_params, and build a where clause using the 
        conjunctive_operator to join segments built from values in field_values 
        which match valid_params in valid_params
        """
        self.__assert_valid_param_type(param_type)
        segments = []
        sorted_params = sorted(valid_params)
        for field_name in sorted_params:
            if field_name in field_values:
                segment = self.__build_segment(
                    param_type, field_name, field_values[field_name])
                segments.append(segment)
        return conjunctive_operator.join(segments)
    
    def build_parameter_list(self, conjunctive_operator, allowed_params, **params):
        segments = []
        for allowed_param in allowed_params:
            if allowed_param in params:
                segments.append('"' + allowed_param + 
                          '" = %(' + allowed_param + ")s")
        if not segments:
            raise ValueError("None of [" ", ".join(allowed_params) 
                         + " in params.")
        return conjunctive_operator.join(segments)
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

__author__ = "Joe Roets, Brandon Kite, Dylan Yelton, Michael Bachtel"
__copyright__ = "Copyright 2016, Disney Connected and Advanced Technologies"
__license__ = "Apache"
__version__ = "2.0"
__maintainer__ = "Joe Roets"
__email__ = "joe@dragonchain.org"

import datetime
import pytz


def format_time(dt):
    return int((dt-datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds())


def format_transaction(txn):
    return {
        "header": {
            "transaction_id":       txn["transaction_id"],
            "transaction_ts":       format_time(txn["transaction_ts"]),
            "create_ts":            format_time(txn["create_ts"]),
            "business_unit":        txn["business_unit"],
            "family_of_business":   txn["family_of_business"],
            "line_of_business":     txn["line_of_business"],
            "owner":                txn["owner"],
            "creator_id":           txn["creator_id"],
            "transaction_type":     txn["transaction_type"],
            "block_id":             txn["block_id"],
            "status":               txn["status"],
            "actor":                txn["actor"],
            "entity":               txn["entity"]
        },
        "payload":   txn["payload"],
        "signature": txn["signature"]
    }


def format_block_verification(block_verification):
    return {
        "verification_id":      block_verification["verification_id"],
        "verified_ts":          format_time(block_verification["verified_ts"]),
        "block_id":             block_verification["block_id"],
        "signature":            block_verification["signature"],
        "origin_id":            block_verification["origin_id"],
        "phase":                block_verification["phase"],
        "verification_info":    block_verification["verification_info"],
        "previous_block_hash":  block_verification["previous_block_hash"]
    }


def format_node(node):
    return {
        "node_id":              node["node_id"],
        "create_ts":            node["create_ts"],
        "node_owner":           node["node_owner"],
        "host":                 node["host"],
        "port":                 node["port"],
        "phases":               node["phases"],
        "latency":              node["latency"],
        "connection_attempts":  node["connection_attempts"],
        "pass_phrase":          node["pass_phrase"]
    }


def format_verification_record(verification_record):
    return {
        "origin_id":            verification_record["origin_id"],
        "transfer_to":          verification_record["transfer_to"],
        "verification_id":      verification_record["verification_id"],
        "sent":                 verification_record["sent"]
    }


def format_subscription(subscription):
    return {
        "subscription_id":          subscription["subscription_id"],
        "subscribed_node_id":       subscription["subscribed_node_id"],
        "host":                     subscription["host"],
        "port":                     subscription["port"],
        "criteria":                 subscription["criteria"],
        "minimum_block_id":         subscription["minimum_block_id"],
        "synchronization_period":   subscription["synchronization_period"],
        "last_time_called":         subscription["last_time_called"],
        "status":                   subscription["status"]
    }

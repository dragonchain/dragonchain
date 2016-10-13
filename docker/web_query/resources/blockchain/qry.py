__author__ = 'bkite'

import tornado.ioloop
import tornado.web
import tornado
import psycopg2
from psycopg2.extras import Json
import logging
import argparse
import json
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
        "owner":                block_verification["owner"],
        "phase":                block_verification["phase"],
        "transaction_info":     block_verification["transaction_info"],
        "previous_block_hash":  block_verification["previous_block_hash"]
    }



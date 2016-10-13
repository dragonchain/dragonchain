__author__ = 'j03'

import time
import calendar

# coin epoch start is May 21, 2015 12:57 PDT = 1432238220 seconds since epoch

class Block(object):
    """

    """
    txs = None
    prior_block_hash = None

    # dictionary of owner/source : {array of tx + hash + signature + public_key}
    approved = None

    # dictionary of validator/source : {array of tx + hash + signature + public_key}
    validated = None

    def __init__(self, txs):
        self.txs = txs

    def verify_phase_1(self):
        pass

    def hash(self):
        pass


EPOCH_OFFSET = 1432238220
BLOCK_INTERVAL = 5

BLOCK_VERIFICATION_OFFSET = 2
BLOCK_FIXATE_OFFSET = 2

def get_block_id(secs_since_epoch):
    # TODO make the 5 sec a constant
    return int(calendar.timegm(time.gmtime(secs_since_epoch - EPOCH_OFFSET))/BLOCK_INTERVAL)

def get_current_block_id():
    # get the seconds in 5 sec intervals
    # interval = int(now.gmtime().tm_sec / BLOCK_INTERVAL) * BLOCK_INTERVAL
    return int((time.time()-EPOCH_OFFSET)/BLOCK_INTERVAL)

def get_next_block_id():
    return get_current_block_id() + 1

def get_block_time(block_id):
    return block_id * BLOCK_INTERVAL + EPOCH_OFFSET

def get_phase_block_id(block_id, phase):
    return block_id - BLOCK_VERIFICATION_OFFSET - phase

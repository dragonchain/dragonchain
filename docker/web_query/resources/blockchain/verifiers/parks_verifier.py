__author__ = 'j03'

import logging
from blockchain.processing import BlockVerifier
from blockchain.block import Block, get_phase_block_id, get_current_block_id
from apscheduler.schedulers.blocking import BlockingScheduler

class ParksVerifier(BlockVerifier):
    """
    Parks BU verification
    """

    def approve(self, txs):
        """Implementation of node/business specific logic to approve _owned_ transactions"""
        print("""Approve""")
        #     if all goes well:
        sig_block = self.sign_transactions(txs, 2)

        # store the sig in the block
        pass

    def separate_txs(self):
        """Implementation of node/business specific separation of transactions into _mine_ and _not_mine_"""
        cur = self.conn.cursor()

        phase_1_block_id = get_phase_block_id(self.current_block_id, 1)
        cur.execute("""SELECT * FROM transaction WHERE block_id = %i AND business_unit = 'parks' """ % phase_1_block_id)
        mine = cur.fetchall()

        cur.execute("""SELECT * FROM transaction WHERE block_id = %i AND business_unit <> 'parks' """ % phase_1_block_id)
        theirs = cur.fetchall()

        print """Transactions: mine=%i theirs=%i""" % (len(mine), len(theirs))

        cur.close()

        return (mine, theirs)

    @staticmethod
    def start_verification_process(private_key, public_key):
        block_id = get_current_block_id()
        verifier = ParksVerifier(block_id, private_key, public_key)
        print "-----------\nBlock %i - verification start." % block_id
        verifier.process()

def main():
    scheduler = BlockingScheduler()
    scheduler.add_job(func=ParksVerifier.start_verification_process,
                      trigger='cron',
                      second='*/5',
                      )
    scheduler.start()

if __name__ == '__main__':
    main()

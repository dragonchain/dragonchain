Run unit tests

1) Set PYTHONPATH environment variable to current path to the dragonchain folder.

    Mac:
    
        export PYTHONPATH=/path/to/dragonchain
        
    Linux:
    
        PYTHONPATH="/path/to/dragonchain"

2) Navigate to dragonchain/blockchain/tests folder and run
    
    python crypto_utest.py

3) If Ok prints out at the end of the script, all tests passed.
   If Failed, the error is displayed where it failed.

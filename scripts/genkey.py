import os
print("PRINTING THE KEY TO THE NETWORK TO key.pem for transaction.py and transaction_svc.py"
key = os.urandom(16)
with open('key.pem','w') as f:
    f.write(key)

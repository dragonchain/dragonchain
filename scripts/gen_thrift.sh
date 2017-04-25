#!/bin/bash
echo Generating Thrift files
thrift -r --gen py ../thrift/messaging.thrift
echo Thrift files generated
sleep 2
echo Copying required files to gen folder
cp gen-py/messaging/ttypes.py ../blockchain/gen/messaging/
cp gen-py/messaging/BlockchainService-remote ../blockchain/gen/messaging/
cp gen-py/messaging/blockchainService.py ../blockchain/gen/messaging/
sleep 1
echo Deleting gen-py directory from Thrift folder
rm -rf gen-py
echo Process complete

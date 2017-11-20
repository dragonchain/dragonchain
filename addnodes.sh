#!/bin/bash
cd scripts/
echo "Please wait for a few moments... About to import nodes (For phase 4 node operation!!)"
sleep 5s
sudo python insert_db.py --owner=blocky -p=8080 --phases=00001
sudo python insert_db.py --owner=blocky -p=8081 --phases=00010
sudo python insert_db.py --owner=blocky -p=8082 --phases=00011
sudo python insert_db.py --owner=blocky -p=8083 --phases=00100
sleep 5s
cd ..

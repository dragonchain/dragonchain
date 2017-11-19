#!/bin/bash
sudo service docker start
cd docker/
echo "Making sure docker containers are ABSOLUTELY UP"
sudo docker-compose up -d
sudo docker-compose up -d
sudo docker-compose up -d
sudo docker-compose up -d
sudo docker-compose up -d
cd ..
cd scripts/
echo "Please wait for a few moments... About to import nodes (For phase 4 node operation!!)"
sleep 5s
sudo python insert_db.py --owner=blocky -p=8080 --phases=00001
sudo python insert_db.py --owner=blocky -p=8081 --phases=00010
sudo python insert_db.py --owner=blocky -p=8082 --phases=00011
sudo python insert_db.py --owner=blocky -p=8083 --phases=00100
sleep 5s
cd ..
export PS1="\e[0;44m[\u@\h \W]\$ \e[m "
cat docs/install.txt

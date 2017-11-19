#!/bin/bash
sudo apt update
sudo apt-get install openssl uuid docker docker-compose python2.7 python-pip postgresql postgresql-server-dev-9.5 screen
export PYTHONPATH=./
sudo python setup.py install
sudo -H pip install -r requirements.txt
cd sql/
echo "Setting up databases... UP TO NODE 5 operation. PLEASE be patient"
sudo useradd blocky
sudo service postgresql start
sudo -u postgres createuser  blocky
sudo -u postgres createdb -O blocky blockchain
sudo -u postgres createdb -O blocky blockchain0
sudo -u postgres createdb -O blocky blockchain1
sudo -u postgres createdb -O blocky blockchain2
sudo -u postgres createdb -O blocky blockchain3
sudo -u postgres createdb -O blocky blockchain4
sudo -u postgres createdb -O blocky blockchain5
sudo -u blocky psql -U blocky -d blockchain -a -f depl.sql
sudo -u blocky psql -U blocky -d blockchain0 -a -f depl.sql
sudo -u blocky psql -U blocky -d blockchain1 -a -f depl.sql
sudo -u blocky psql -U blocky -d blockchain2 -a -f depl.sql
sudo -u blocky psql -U blocky -d blockchain3 -a -f depl.sql
sudo -u blocky psql -U blocky -d blockchain4 -a -f depl.sql
sudo -u blocky psql -U blocky -d blockchain5 -a -f depl.sql
sudo service postgresql stop
cd ..
sudo mkdir pki/
sudo openssl ecparam -name secp224r1 -genkey -out pki/sk.pem
sudo openssl ec -in pki/sk.pem -pubout -out pki/pk.pem
sudo mkdir logs/
cd configs/
str=`cat template.yml`
find="XXXXXXXXX"
replace=`uuid`
result=${str//$find/$replace}
echo "$result" > blockchain.yml
cd ..
sudo service docker start
cd docker/
sudo docker-compose up -d
sudo docker-compose up -d
cd ..
cd scripts/
echo "Please wait for a few moments... About to import nodes (For phase 4 node operation!!)"
sleep 7s
sudo python insert_db.py --owner=blocky -p=8080 --phases=00001
sudo python insert_db.py --owner=blocky -p=8081 --phases=00010
sudo python insert_db.py --owner=blocky -p=8082 --phases=00011
sudo python insert_db.py --owner=blocky -p=8083 --phases=00100
sleep 7s
cd ..
cd docker/
sudo docker-compose restart
cd ..
export PS1="\e[0;44m[\u@\h \W]\$ \e[m "
cat docs/install.txt
export PS1="\e[0;39m[\u@\h \W]\$ \e[m "

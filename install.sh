#!/bin/bash
sudo apt update
sudo apt-get install openssl docker docker-compose python2.7 python-pip postgresql postgresql-server-dev-9.5
sudo pip install -r requirements.txt
sudo python setup.py install
cd sql/
sudo useradd blocky
sudo service postgresql start
sudo -u postgres createuser  blocky
sudo -u postgres createdb -O blocky blockchain
sudo -u blocky psql -U blocky -d blockchain -a -f depl.sql
sudo service postgresql stop
cd ..
sudo mkdir pki/
sudo openssl ecparam -name secp224r1 -genkey -out pki/sk.pem
sudo openssl ec -in pki/sk.pem -pubout -out pki/pk.pem
sudo mkdir logs/
export PYTHONPATH=$PWD
sudo service docker start
cd docker/
sudo docker-compose up -d
echo "Containers have been brought up, to start and stop make sure you are in the docker/ directory and then do: sudo docker-compose up -d"
echo "To bring down the container: sudo docker-compose down"
echo "Make sure to do this in shell: export PYTHONPATH=/home/yourusername/dragonchain"
echo "Make sure to run commands in docker with: docker exec -it container_id_or_name commandhere"

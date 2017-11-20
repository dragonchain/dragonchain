#!/bin/bash
echo "About to drop databases... you've got 15 seconds to cancel..."
sleep 15s
sudo service postgresql start
sudo -u blocky dropdb blockchain
sudo -u blocky dropdb blockchain0
sudo -u blocky dropdb blockchain1
sudo -u blocky dropdb blockchain2
sudo -u blocky dropdb blockchain3
sudo -u blocky dropdb blockchain4
sudo -u blocky dropdb blockchain5
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
echo "databases have been recreated after being dropped..."

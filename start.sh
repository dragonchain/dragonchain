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
export PS1="\e[0;44m[\u@\h \W]\$ \e[m "
echo "DONE"
cat docs/install.txt
echo "DONE"

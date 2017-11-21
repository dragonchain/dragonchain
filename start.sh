#!/bin/bash
export PS1="\e[0;44m[\u@\h \W]\$ "
clear
sudo service docker start
cd docker/
echo "Making sure docker containers are ABSOLUTELY UP"
sudo docker-compose up -d
sudo docker-compose up -d
sudo docker-compose up -d
sudo docker-compose up -d
sudo docker-compose up -d
cd ..
echo "DONE"
cat docs/install.txt
echo "DONE"

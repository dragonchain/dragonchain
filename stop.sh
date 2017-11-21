#!/bin/bash
export PS1="\e[0;44m[\u@\h \W]\$ "
clear
echo "Stopping Containers!"
sudo service docker start
cd docker/
echo "Making sure docker containers are ABSOLUTELY DOWN"
sudo docker-compose down
sudo docker-compose down
sudo docker-compose down
sudo docker-compose down
sudo docker-compose down
cd ..
echo "DONE"
cat docs/install.txt
echo "DONE"

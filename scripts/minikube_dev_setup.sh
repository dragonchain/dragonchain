#!/bin/sh
# Set docker context to minikube
eval $(minikube docker-env)

# Run docker registry if not already started (ignore error)
docker run -d -p 5000:5000 --restart=always --name registry registry:2 2> /dev/null
exit 0

echo You can now push to localhost:5000 and pull it in minikube

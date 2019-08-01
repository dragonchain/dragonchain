#!/bin/sh
# Build and push dependency container
docker build . -f cicd/Dockerfile.dependencies -t "dragonchain/dragonchain_core_dependencies:latest" --no-cache --pull
docker push "dragonchain/dragonchain_core_dependencies:latest"

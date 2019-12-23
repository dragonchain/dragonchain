#!/bin/sh
set -e

# Use arcitecture from ARCHITECTURE env var if provided (like in CI/CD, else just use this computer's arcitecture)
if [ "$ARCHITECTURE" = "amd64" ]; then
    arch="x86_64"
elif [ "$ARCHITECTURE" = "arm64" ]; then
    arch="aarch64"
else
    arch="$(uname -m)"
fi

if [ "$arch" = "x86_64" ]; then
    TAG="linux-amd64-latest"
    docker build . -f cicd/Dockerfile.dependencies -t "dragonchain/dragonchain_core_dependencies:$TAG" --no-cache --pull
elif [ "$arch" = "aarch64" ]; then
    TAG="linux-arm64-latest"
    docker build . -f cicd/Dockerfile.dependencies.arm64 -t "dragonchain/dragonchain_core_dependencies:$TAG" --no-cache --pull
else
    echo "Unknown architecture $arch"
    exit 1
fi

docker push "dragonchain/dragonchain_core_dependencies:$TAG"
rm -rf "$HOME/.docker/manifests/docker.io_dragonchain_dragonchain_core_dependencies-latest/"
if docker manifest create dragonchain/dragonchain_core_dependencies:latest dragonchain/dragonchain_core_dependencies:linux-amd64-latest dragonchain/dragonchain_core_dependencies:linux-arm64-latest; then
    docker manifest push dragonchain/dragonchain_core_dependencies:latest
fi

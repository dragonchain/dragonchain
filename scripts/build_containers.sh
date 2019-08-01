#!/bin/sh
set -e
. .env
if [ -z "$STAGE" ]; then echo "STAGE variable is missing from .env file"; exit 1; fi
if [ -z "$AWS_DEFAULT_REGION" ]; then echo "AWS_DEFAULT_REGION variable is missing from .env file"; exit 1; fi
VERSION=$(cat .version)
TAG=$STAGE-$VERSION

if [ $# -lt 1 ]; then
  # Default to our AWS repos
  $(aws ecr get-login --no-include-email --region us-west-2)
  REPOSITORY=381978683274.dkr.ecr.us-west-2.amazonaws.com
else
  REPOSITORY=$1
fi

echo STAGE "$STAGE"
echo VERSION "$VERSION"
echo REGION "$AWS_DEFAULT_REGION"
echo REPOSITORY "$REPOSITORY"
echo TAG "$TAG"

sleep 4 # Let user see this output and give time to cancel script if something looks wrong

docker build . -t "$REPOSITORY/dragonchain_core:$TAG" --pull

docker push "$REPOSITORY/dragonchain_core:$TAG"

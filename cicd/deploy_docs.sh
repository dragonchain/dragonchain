#!/bin/sh
set -e

if [ "$STAGE" = "prod" ]; then
    echo Pushing built docs to production site
    aws s3 rm --recursive s3://dragonchain-core-docs/latest/*
    aws s3 cp --recursive ./docs/.build/html s3://dragonchain-core-docs/latest
    aws s3 rm --recursive s3://dragonchain-core-docs/$VERSION/*
    aws s3 cp --recursive ./docs/.build/html s3://dragonchain-core-docs/$VERSION
    aws s3api put-object --website-redirect-location /latest --content-type text/html --bucket dragonchain-core-docs --key index.html
elif [ "$STAGE" = "dev" ]; then
    echo Pushing built docs to dev site
    aws s3 rm --recursive s3://dragonchain-core-docs/dev/*
    aws s3 cp --recursive ./docs/.build/html s3://dragonchain-core-docs/dev
fi

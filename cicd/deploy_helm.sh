#!/bin/sh
set -e

if [ "$STAGE" = "prod" ]; then
    echo Packaging and uploading helm chart to public repository
    CHART_FILE="$(helm package helm/dragonchain-k8s/ | grep -o '/.*\.tgz')"
    helm s3repo add dragonchain-charts "$CHART_FILE" -n
elif [ "$STAGE" = "dev" ]; then
    echo Not uploading development helm chart
fi

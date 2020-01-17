#!/bin/sh
set -e

# Check and try to use python3.8 explicitly, if possible
if command -v python3.8 > /dev/null 2>&1; then
    py_exec=python3.8
else
    py_exec=python3
fi

# Makes sure we're in this script's directory (avoid symlinks and escape special chars)
cd "$(cd "$(dirname "$0")"; pwd -P)"

USAGE="usage: tools.sh [command]

command
unit         : run unit tests on the project
coverage     : view coverage for the project (must run unit first)
tests        : run all tests for the project and display coverage when finished
lint         : check that the project has no linting errors with black
format       : automatically try to fix any linting problems that exist with the black formatter
bandit       : run security linting with bandit against the project
docs         : generate the docs and place them into docs/.build
arch-install : install dependencies for arch based systems
deb-install  : install dependencies for debian (and derivatives like ubuntu) based systems
mac-install  : install dependencies for MacOS systems with brew
pip-install  : install python dependencies with pip
clean        : remove compiled python/docs/other build or distribution artifacts from the local project
cicd-update  : update cloudformation for the CICD
full-test    : run all the checks that a PR will test for
docker-test  : run all the checks in a docker container that a PR will test for
version      : perform a version bump"

if [ $# -lt 1 ]; then
    printf "%s\\n" "$USAGE"
    exit 1
elif [ "$1" = "unit" ]; then
    $py_exec -m coverage run --branch --source=./dragonchain -m unittest discover -p '*utest.py'
elif [ "$1" = "coverage" ]; then
    include=$(find dragonchain -path "*.py" -not -path ".git*" -not -path ".mypy_cache*" -not -path ".venv*" | tr '\n' ',' | rev | cut -c 2- | rev)
    $py_exec -m coverage report -m --include="$include"
    $py_exec -m coverage xml --include="$include"
    mv coverage.xml docs/ # Move our coverage file for docker tests with mounted docs
elif [ "$1" = "tests" ]; then
    sh tools.sh unit
    sh tools.sh coverage
elif [ "$1" = "lint" ]; then
    test "$(tail -c 1 .version)" || (printf "Bad newline at end of version file\\nRun tools.sh version" && exit 1)
    if ! grep "appVersion: $(cat .version)" helm/dragonchain-k8s/Chart.yaml > /dev/null 2>&1; then printf "Helm Chart.yaml appVersion doesn't match .version file\\nRun tools.sh version\\n" && exit 1; fi
    if ! grep "version: $(cat .version)" helm/dragonchain-k8s/values.yaml > /dev/null 2>&1; then printf "Helm values.yaml version doesn't match .version file\\nRun tools.sh version\\n" && exit 1; fi
    if ! grep "version: $(cat .version)" helm/opensource-config.yaml > /dev/null 2>&1; then printf "Helm opensource-config.yaml version doesn't match .version file\\nRun tools.sh version\\n" && exit 1; fi
    helm lint helm/dragonchain-k8s/ --strict
    find dragonchain -name "*.py" -exec $py_exec -m flake8 {} +
    $py_exec -m black --check -l 150 -t py38 dragonchain
elif [ "$1" = "format" ]; then
    $py_exec -m black -l 150 -t py38 dragonchain
elif [ "$1" = "bandit" ]; then
    $py_exec -m bandit -r dragonchain
elif [ "$1" = "docs" ]; then
    rm -rf docs/static/chart && mkdir -p docs/static/chart
    cp -v helm/opensource-config.yaml docs/static/chart/
    CHART_VERSION="$(yq r helm/dragonchain-k8s/Chart.yaml version)"
    sed -i "s/--version [0-9]\\{1,\\}\\.[0-9]\\{1,\\}\\.[0-9]\\{1,\\}/--version $CHART_VERSION/" docs/deployment/deploying.md
    (
        cd docs || exit 1
        make html
    )
elif [ "$1" = "arch-install" ]; then
    sudo pacman -Sy base-devel libsecp256k1
elif [ "$1" = "deb-install" ]; then
    sudo apt install -y build-essential automake pkg-config libtool libffi-dev libgmp-dev
elif [ "$1" = "mac-install" ]; then
    brew install automake pkg-config libtool libffi gmp
elif [ "$1" = "pip-install" ]; then
    $py_exec -m pip install --upgrade setuptools --user
    $py_exec -m pip install -r requirements.txt --user
    $py_exec -m pip install -r dev_requirements.txt --user
elif [ "$1" = "clean" ]; then
    find . \( -path ./.venv -o -path ./.mypy_cache \) -prune -o \( -name __pycache__ -o -name .build -o -name .coverage -o -name coverage.xml \) -exec rm -rfv {} +
elif [ "$1" = "cicd-update" ]; then
    aws cloudformation deploy --stack-name Dragonchain-CICD --template-file ./cicd/CICD.cft.yml --capabilities CAPABILITY_NAMED_IAM --no-fail-on-empty-changeset
elif [ "$1" = "docker-test" ]; then
    if [ "$(uname -m)" = "x86_64" ]; then
        docker build . -f ./cicd/Dockerfile.test -t dragonchain_testing_container --pull
    elif [ "$(uname -m)" = "aarch64" ]; then
        docker build . -f ./cicd/Dockerfile.test.arm64 -t dragonchain_testing_container --pull
    fi
    docker run -it -v "$(pwd)":/usr/src/core dragonchain_testing_container
elif [ "$1" = "full-test" ]; then
    set +e
    printf "\\nChecking for linting errors\\n\\n"
    if ! sh tools.sh lint; then printf "\\n!!! Linting Failure. You may need to run 'tools.sh format' !!!\\n" && exit 1; fi
    printf "\\nChecking for static security analysis issues\\n\\n"
    if ! sh tools.sh bandit; then printf "\\n!!! Bandit (Security) Failure !!!\\n" && exit 1; fi
    printf "\\nChecking that the docs can build\\n\\n"
    if ! sh tools.sh docs; then printf "\\n!!! Docs Build Failure!!!\\n" && exit 1; fi
    printf "\\nRunning all tests\\n\\n"
    if ! sh tools.sh tests; then printf "\\n!!! Tests Failure !!!\\n" && exit 1; fi
    printf "\\nSuccess!\\nUse 'tools.sh clean' to cleanup if desired\\n"
elif [ "$1" = "version" ]; then
    set +e
    semver="$(echo "$2" | grep '^[0-9]\{1,\}\.[0-9]\{1,\}\.[0-9]\{1,\}$')"
    set -e
    if [ -z "$semver" ]; then printf "Version must be provided and valid semvar\\nex: tools.sh version 1.2.3\\n" && exit 1; fi
    printf "%s" "$semver" > .version
    sed -i "s/appVersion:.*/appVersion: $semver/" helm/dragonchain-k8s/Chart.yaml
    sed -i "s/version:.*/version: $semver/" helm/dragonchain-k8s/values.yaml
    sed -i "s/version:.*/version: $semver/" helm/opensource-config.yaml
else
    printf "%s\\n" "$USAGE"
    exit 1
fi

#!/bin/sh
set -e

# Check and try to use python3.7 explicitly, if possible
if command -v python3.7 > /dev/null 2> /dev/null; then
    py_exec=python3.7
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
clean        : remove compiled python/docs/other build or distrubition artifacts from the local project
cicd-update  : update cloudformation for the CICD
full-test    : run all the checks that a PR will test for"

if [ $# -ne 1 ]; then
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
    find dragonchain -name "*.py" -exec $py_exec -m flake8 {} +
    $py_exec -m black --check -l 150 -t py37 dragonchain
    test "$(tail -c 1 .version)" || (printf "Bad newline at end of version file!" && exit 1)
elif [ "$1" = "format" ]; then
    $py_exec -m black -l 150 -t py37 dragonchain
elif [ "$1" = "bandit" ]; then
    $py_exec -m bandit -r dragonchain
elif [ "$1" = "docs" ]; then
    rm -rf docs/static/chart && mkdir -p docs/static/chart
    helm package helm/dragonchain-k8s -d docs/static/chart/
    cp -v helm/opensource-config.yaml docs/static/chart/
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
    aws cloudformation update-stack --stack-name Dragonchain-CICD --template-body file://./cicd/CICD.cft.yml --region us-west-2  --profile default --capabilities CAPABILITY_NAMED_IAM
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
else
    printf "%s\\n" "$USAGE"
    exit 1
fi

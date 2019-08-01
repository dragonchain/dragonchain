#!/bin/sh
set -e
python3 -m dragonchain.webserver.start
gunicorn -c python:dragonchain.webserver.gunicorn_settings dragonchain.webserver.app:app

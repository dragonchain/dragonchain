#!/usr/bin/env bash

function initDB() {
    createdb -U postgres blockchain
    cd /usr/share/sql
    psql -U postgres -d blockchain -a -f depl.sql
}

initDB
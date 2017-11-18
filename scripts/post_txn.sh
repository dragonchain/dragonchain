#!/bin/bash
str=`cat valid_payload.json`
find="1475180987"
replace=`date +"%s"`
result=${str//$find/$replace}
echo "$result"

curl -H 'Accept-Encoding: gzip,deflate' -X POST http://localhost:81/transaction -d "$result"

#!/bin/bash
str=`cat provisionTSC.json`
find="XXXXXXXXX"
replace=`date +"%s"`
result=${str//$find/$replace}
echo "$result"

curl -H 'Accept-Encoding: gzip,deflate' -X POST http://localhost:81/transaction -d "$result"

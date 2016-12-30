#!/bin/bash
curl -H 'Accept-Encoding: gzip,deflate' -X POST http://localhost:8000/transaction -d @valid_payload.json
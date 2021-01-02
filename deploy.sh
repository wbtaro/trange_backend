#!/bin/bash

cd venv/lib/python3.9/site-packages/
zip -r9 ${OLDPWD}/function.zip .
cd $OLDPWD 
zip -g function.zip source/range_search.py

aws lambda update-function-code --function-name Trange_range_search --zip-file fileb://function.zip

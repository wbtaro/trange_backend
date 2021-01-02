#!/bin/bash

# 範囲検索用のLambda関数のデプロイ
cd venv/lib/python3.9/site-packages/
zip -r9 ${OLDPWD}/function.zip .
cd $OLDPWD 
zip -g function.zip source/range_search.py

aws lambda update-function-code --function-name Trange_range_search --zip-file fileb://function.zip

zip -d function.zip source/range_search.py

# インクリメンタルサーチ用Lambda関数のデプロイ
zip -g function.zip source/incremental_search.py

aws lambda update-function-code --function-name Trange_incremental_search --zip-file fileb://function.zip

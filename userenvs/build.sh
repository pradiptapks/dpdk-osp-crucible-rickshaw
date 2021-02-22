#!/bin/bash

if [ -z "$1" ]; then
    echo "You must provide a directory"
    exit
fi

userenv="$1"
if [ ! -d "$userenv" ]; then
    echo "Directory $userenv not found"
    exit 1
fi


pushd "$userenv"
echo "{" >../staging.json
cat schema.json >>../staging.json
cat userenv.json >>../staging.json
pushd requirements
echo '  "requirements": [' >>../../staging.json
count=0
for i in `/bin/ls -1`; do
    if [ $count -gt 0 ]; then
        echo ',' >>../../staging.json
    fi
    echo "found $i"
    cat $i >>../../staging.json
    let count=$count+1
done
popd
echo ']' >>../staging.json
echo '}' >>../staging.json
popd
jq . staging.json >$userenv.json && \
/bin/rm staging.json


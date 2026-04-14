#!/usr/bin/env bash

set -ex

if [ -z "$1" ]; then
    echo "Usage: $0 <docker-image>"
    exit 1
fi

# git clean -fd
git checkout pnpm-migration

# Copy script.sh to current working directory

Docker_image="$1"

docker run --rm -v $PWD:/app -w /app --entrypoint sh $Docker_image script.sh

rm script.sh
git add .
git commit -m "Pushed conversion of npm to pnpm changes"
git push

echo "Done."
#!/usr/bin/env bash

set -ex

pushd ../../

sugar build
sugar ext restart --options -d
sleep 5

popd

celery -A tasks.app worker --loglevel=debug &
python app.py

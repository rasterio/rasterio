#!/usr/bin/env bash

set -e

# If Cython and Numpy aren't installed at this stage, build wheels for all
# the dev requirements and then install them.
if [[ -n "$( pip list | grep -i cython)" && -n "$( pip list | grep -i numpy)" ]]
then
    echo "Cython and Numpy found in wheelhouse."
else
    echo "Building all dev wheels..."
    pip wheel --wheel-dir=/tmp/wheelhouse -r requirements-dev.txt
    pip install --pre --use-wheel --no-index --find-links=/tmp/wheelhouse -r requirements-dev.txt
fi

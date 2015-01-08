#!/bin/bash

# Automation of this is a TODO. For now, it depends on manually built libraries
# as detailed in https://gist.github.com/sgillies/a8a2fb910a98a8566d0a.

export MACOSX_DEPLOYMENT_TARGET=10.6
export GDAL_CONFIG="/usr/local/bin/gdal-config"
export PACKAGE_DATA=1

VERSION=$1

source $HOME/envs/riowhl27/bin/activate
CFLAGS="`$GDAL_CONFIG --cflags`" LDFLAGS="`$GDAL_CONFIG --libs` `$GDAL_CONFIG --dep-libs`" python setup.py bdist_wheel -d wheels/$VERSION
source $HOME/envs/riowhl34/bin/activate
CFLAGS="`$GDAL_CONFIG --cflags`" LDFLAGS="`$GDAL_CONFIG --libs` `$GDAL_CONFIG --dep-libs`" python setup.py bdist_wheel -d wheels/$VERSION

parallel delocate-wheel -w fixed_wheels/$VERSION --require-archs=intel -v {} ::: wheels/$VERSION/*.whl
parallel cp {} {.}.macosx_10_9_intel.macosx_10_9_x86_64.macosx_10_10_intel.macosx_10_10_x86_64.whl ::: fixed_wheels/$VERSION/*.whl

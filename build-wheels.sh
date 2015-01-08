#!/bin/bash

# Automation of this is a TODO. For now, it depends on manually built libraries
# as detailed in https://gist.github.com/sgillies/a8a2fb910a98a8566d0a.

export MACOSX_DEPLOYMENT_TARGET=10.7
export GDAL_CONFIG="/usr/local/bin/gdal-config"
export PACKAGE_DATA=1

VERSION=$1

source $HOME/envs/riowhl27/bin/activate
CFLAGS="`$GDAL_CONFIG --cflags`" LDFLAGS="`$GDAL_CONFIG --libs` `$GDAL_CONFIG --dep-libs`" python setup.py bdist_wheel -d wheels/$VERSION
source $HOME/envs/riowhl34/bin/activate
CFLAGS="`$GDAL_CONFIG --cflags`" LDFLAGS="`$GDAL_CONFIG --libs` `$GDAL_CONFIG --dep-libs`" python setup.py bdist_wheel -d wheels/$VERSION

find wheels/$VERSION -name rasterio-$VERSION*.whl -exec delocate-wheel -w fixed_wheels/$VERSION --require-archs=intel -v {} \;
find fixed_wheels/$VERSION -name *.whl -exec rename s/macosx_10_6_intel/macosx_10_6_intel.macosx_10_9_intel.macosx_10_9_x86_64/ {} \;

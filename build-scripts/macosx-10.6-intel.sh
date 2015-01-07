#!/bin/bash

# Dependent on the Kyngchaos Frameworks:
# http://www.kyngchaos.com/software/frameworks

export MACOSX_DEPLOYMENT_TARGET=10.7
export GDAL_CONFIG="gdal-config"
CFLAGS="`$GDAL_CONFIG --cflags`" LDFLAGS="`$GDAL_CONFIG --libs` `$GDAL_CONFIG --dep-libs`" python setup.py bdist_wheel
delocate-wheel -w fixed_wheels --require-archs=intel -v dist/rasterio-0.16-cp27-none-macosx_10_6_intel.whl
mv fixed_wheels/rasterio-0.16-cp27-none-macosx_10_6_intel.whl fixed_wheels/rasterio-0.16-cp27-none-macosx_10_6_intel.macosx_10_9_intel.macosx_10_9_x86_64.whl

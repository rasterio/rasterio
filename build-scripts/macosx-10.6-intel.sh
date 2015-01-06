#!/bin/bash

# Dependent on the Kyngchaos Frameworks:
# http://www.kyngchaos.com/software/frameworks

export GDAL_CONFIG="/Library/Frameworks/GDAL.framework/unix/bin/gdal-config"
CFLAGS="`$GDAL_CONFIG --cflags`" LDFLAGS="`$GDAL_CONFIG --libs`" python setup.py bdist_wheel
delocate-wheel -w fixed_wheels --require-archs=intel -v dist/rasterio-0.16-cp27-none-macosx_10_6_intel.whl

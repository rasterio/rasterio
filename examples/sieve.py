#!/usr/bin/env python
#
# sieve: demonstrate sieving and polygonizing of raster features.

import subprocess

import numpy
import rasterio
from rasterio.features import sieve, shapes


# Register GDAL and OGR drivers
with rasterio.drivers():
    
    # Read a raster to be sieved.
    with rasterio.open('rasterio/tests/data/shade.tif') as src:
        shade = src.read_band(1)
    
    # Print the number of shapes.
    print "Slope shapes: %d" % len(list(shapes(shade)))
    
    # Sieve out features 13 pixels or smaller
    sieved = sieve(shade, 13)

    # Print the number of sieved shapes
    print "Sieved (13) shapes: %d" % len(list(shapes(sieved)))

    # Write out the sieved features
    with rasterio.open('example-sieved.tif', 'w', **src.meta) as dst:
        dst.write_band(1, sieved)

# Dump out gdalinfo's report card and open the image.
info = subprocess.check_output(
    ['gdalinfo', '-stats', 'example-sieved.tif'])
print(info)
subprocess.call(['open', 'example-sieved.tif'])


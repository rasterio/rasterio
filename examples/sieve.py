#!/usr/bin/env python
#
# sieve: demonstrate sieving and polygonizing of raster features.

import subprocess

import numpy as np
import rasterio
from rasterio.features import sieve, shapes


# Register GDAL and OGR drivers.
with rasterio.drivers():
    
    # Read a raster to be sieved.
    with rasterio.open('tests/data/shade.tif') as src:
        shade = src.read(1)
    
    # Print the number of shapes in the source raster.
    print("Slope shapes: %d" % len(list(shapes(shade))))
    
    # Sieve out features 13 pixels or smaller.
    sieved = sieve(shade, 13, out=np.zeros(src.shape, src.dtypes[0]))

    # Print the number of shapes in the sieved raster.
    print("Sieved (13) shapes: %d" % len(list(shapes(sieved))))

    # Write out the sieved raster.
    kwargs = src.meta
    kwargs['transform'] = kwargs.pop('affine')
    with rasterio.open('example-sieved.tif', 'w', **kwargs) as dst:
        dst.write(sieved, indexes=1)

# Dump out gdalinfo's report card and open (or "eog") the TIFF.
print(subprocess.check_output(
    ['gdalinfo', '-stats', 'example-sieved.tif']))
subprocess.call(['open', 'example-sieved.tif'])


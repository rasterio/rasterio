import os
import shutil
import subprocess
import tempfile

import numpy
import rasterio
from rasterio.warp import reproject, RESAMPLING

tempdir = '/tmp'
tiffname = os.path.join(tempdir, 'example.tif')

with rasterio.drivers():

    # Consider a 512 x 512 raster centered on 0 degrees E and 0 degrees N
    # with each pixel covering 15".
    src_shape = (512, 512)
    src_transform = [-256.0/240, 1.0/240, 0.0, 256.0/240, 0.0, -1.0/240]
    src_crs = {'init': 'EPSG:4326'}
    source = numpy.ones(src_shape, numpy.uint8)*255

    # Prepare to reproject this rasters to a 1024 x 1024 dataset in
    # Web Mercator (EPSG:3857) with origin at -8928592, 2999585.
    dst_shape = (1024, 1024)
    dst_transform = [-237481.5, 425.0, 0.0, 237536.4, 0.0, -425.0]
    dst_crs = {'init': 'EPSG:3857'}
    destination = numpy.zeros(dst_shape, numpy.uint8)

    reproject(
        source, 
        destination, 
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        resampling=RESAMPLING.nearest)

    # Assert that the destination is only partly filled.
    assert destination.any()
    assert not destination.all()

    # Write it out to a file.
    with rasterio.open(
            tiffname, 
            'w',
            driver='GTiff',
            width=dst_shape[1],
            height=dst_shape[0],
            count=1,
            dtype=numpy.uint8,
            nodata=0,
            transform=dst_transform,
            crs=dst_crs) as dst:
        dst.write_band(1, destination)

info = subprocess.call(['open', tiffname])


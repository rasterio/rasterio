import os.path
import subprocess
import tempfile

import rasterio

with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
    b = src.read_band(1)
    g = src.read_band(2)
    r = src.read_band(3)
    meta = src.meta

outfilename = os.path.join(tempfile.mkdtemp(), 'decimate.tif')

meta.update(
    width=src.width/2,
    height=src.height/2)

with rasterio.open(
        outfilename, 'w',
        dtype=rasterio.uint8,
        **meta
        ) as dst:
    dst.write_band(1, b)
    dst.write_band(2, g)
    dst.write_band(3, r)

info = subprocess.call(['open', outfilename])


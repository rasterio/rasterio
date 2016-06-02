import os.path
import subprocess
import tempfile

import rasterio

with rasterio.Env():

    with rasterio.open('tests/data/RGB.byte.tif') as src:
        b, g, r = (src.read(k) for k in (1, 2, 3))
        meta = src.meta

    tmpfilename = os.path.join(tempfile.mkdtemp(), 'decimate.tif')

    meta.update(
        width=src.width/2,
        height=src.height/2)

    with rasterio.open(
            tmpfilename, 'w',
            **meta
            ) as dst:
        for k, a in [(1, b), (2, g), (3, r)]:
            dst.write(a, indexes=k)

    outfilename = os.path.join(tempfile.mkdtemp(), 'decimate.jpg')

    rasterio.copy(tmpfilename, outfilename, driver='JPEG', quality='30')

info = subprocess.call(['open', outfilename])

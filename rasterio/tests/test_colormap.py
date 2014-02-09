import logging
import pytest
import subprocess
import sys

import rasterio

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

def test_write_colormap(tmpdir):

    with rasterio.drivers():

        with rasterio.open('rasterio/tests/data/shade.tif') as src:
            shade = src.read_band(1)
            meta = src.meta

        tiffname = str(tmpdir.join('foo.tif'))
        
        with rasterio.open(tiffname, 'w', **meta) as dst:
            dst.write_band(1, shade)
            dst.write_colormap(1, {0: (255, 0, 0, 255), 255: (0, 0, 255, 255)})
            cmap = dst.read_colormap(1)
            assert cmap[0] == (255, 0, 0, 255)
            assert cmap[255] == (0, 0, 255, 255)

        with rasterio.open(tiffname) as src:
            cmap = src.read_colormap(1)
            assert cmap[0] == (255, 0, 0, 255)
            assert cmap[255] == (0, 0, 255, 255)

    # subprocess.call(['open', tiffname])


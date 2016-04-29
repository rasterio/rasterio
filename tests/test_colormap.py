import logging
import subprocess
import sys

import rasterio


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_write_colormap_warn(tmpdir, recwarn):
    with rasterio.open('tests/data/shade.tif') as src:
        profile = src.meta
    tiffname = str(tmpdir.join('foo.tif'))
    with rasterio.open(tiffname, 'w', **profile) as dst:
        dst.write_colormap(1, {0: (255, 0, 0, 255), 255: (0, 0, 0, 0)})
    w = recwarn.pop(UserWarning)
    assert "The value will be ignored" in str(w.message)


def test_write_colormap(tmpdir):
    with rasterio.open('tests/data/shade.tif') as src:
        shade = src.read(1)
        meta = src.meta
    tiffname = str(tmpdir.join('foo.png'))
    meta['driver'] = 'PNG'
    with rasterio.open(tiffname, 'w', **meta) as dst:
        dst.write(shade, indexes=1)
        dst.write_colormap(1, {0: (255, 0, 0, 255), 255: (0, 0, 0, 0)})
        cmap = dst.colormap(1)
        assert cmap[0] == (255, 0, 0, 255)
        assert cmap[255] == (0, 0, 0, 0)
    with rasterio.open(tiffname) as src:
        cmap = src.colormap(1)
        assert cmap[0] == (255, 0, 0, 255)
        assert cmap[255] == (0, 0, 0, 0)

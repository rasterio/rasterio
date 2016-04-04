import pytest

import rasterio
from rasterio.enums import ColorInterp, PhotometricInterp


def test_cmyk_interp(tmpdir):
    """A CMYK TIFF has cyan, magenta, yellow, black bands."""
    with rasterio.drivers():
        with rasterio.open('tests/data/RGB.byte.tif') as src:
            meta = src.meta
        meta['photometric'] = 'CMYK'
        meta['count'] = 4
        tiffname = str(tmpdir.join('foo.tif'))
        with rasterio.open(tiffname, 'w', **meta) as dst:
            assert dst.profile['photometric'] == 'cmyk'
            assert dst.colorinterp(1) == ColorInterp.cyan
            assert dst.colorinterp(2) == ColorInterp.magenta
            assert dst.colorinterp(3) == ColorInterp.yellow
            assert dst.colorinterp(4) == ColorInterp.black


def test_ycbcr_interp(tmpdir):
    """A YCbCr TIFF has red, green, blue bands."""
    with rasterio.drivers():
        with rasterio.open('tests/data/RGB.byte.tif') as src:
            meta = src.meta
        meta['photometric'] = 'ycbcr'
        meta['compress'] = 'jpeg'
        meta['count'] = 3
        tiffname = str(tmpdir.join('foo.tif'))
        with rasterio.open(tiffname, 'w', **meta) as dst:
            assert dst.colorinterp(1) == ColorInterp.red
            assert dst.colorinterp(2) == ColorInterp.green
            assert dst.colorinterp(3) == ColorInterp.blue

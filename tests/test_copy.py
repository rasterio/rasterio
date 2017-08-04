"""Tests for ``rasterio.copy()``."""

import numpy

import pytest

import rasterio
from rasterio._err import CPLE_NotSupportedError
from rasterio.errors import DriverRegistrationError


@pytest.mark.parametrize("pass_handle", (True, False))
def test_copy(tmpdir, path_rgb_byte_tif, pass_handle):

    """Ensure ``rasterio.copy()`` can read from a path to a file on disk
    and an open dataset handle.
    """

    outfile = str(tmpdir.join('test_copy.tif'))

    if pass_handle:
        src = rasterio.open(path_rgb_byte_tif)
    else:
        src = path_rgb_byte_tif

    rasterio.copy(
        src,
        outfile,
        # Test a mix of boolean, ints, and strings to make sure creation
        # options passed as Python types are properly cast.
        tiled=True,
        blockxsize=512,
        BLOCKYSIZE='256')

    if isinstance(src, str):
        src = rasterio.open(path_rgb_byte_tif)

    with rasterio.open(outfile) as dst:
        assert dst.driver == 'GTiff'
        assert set(dst.block_shapes) == {(256, 512)}

        src_data = src.read()
        dst_data = dst.read()

        assert numpy.array_equal(src_data, dst_data)

    src.close()


def test_bad_driver():
    with pytest.raises(DriverRegistrationError):
        rasterio.copy('tests/data/RGB.byte.tif', None, driver='trash')


def test_copy_strict_failure(tmpdir, path_float_tif):
    """Ensure that strict=True raises an exception
     for a bad write instead of failing silently."""

    outfile = str(tmpdir.join('test_copy.jpg'))

    with pytest.raises(CPLE_NotSupportedError):
        rasterio.copy(
            path_float_tif, outfile, strict=True,
            driver='JPEG')


def test_copy_strict_silent_failure(tmpdir, path_float_tif):
    """Ensure that strict=False allows a bad write
    to fail silently.  The raster will exist but
    will not be valid"""

    outfile = str(tmpdir.join('test_copy.jpg'))

    rasterio.copy(
        path_float_tif, outfile, strict=False,
        driver='JPEG')

    with rasterio.open(outfile) as dst:
        assert dst.driver == 'JPEG'
        assert dst.read().max() == 0  # it should be 1.4099; 0 indicates bad data



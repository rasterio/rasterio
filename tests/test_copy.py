"""Tests for ``rasterio.copy()``."""


import pytest

import rasterio
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

    try:
        rasterio.copy(
            src,
            outfile,
            # Test a mix of boolean, ints, and strings to make sure creation
            # options passed as Python types are properly cast.
            tiled=True,
            blockxsize=512,
            BLOCKYSIZE='256')

    finally:
        if not isinstance(src, str):
            src.close()

    with rasterio.open(outfile) as src:
        assert src.driver == 'GTiff'
        assert set(src.block_shapes) == {(256, 512)}


def test_bad_driver():
    with pytest.raises(DriverRegistrationError):
        rasterio.copy('tests/data/RGB.byte.tif', None, driver='trash')

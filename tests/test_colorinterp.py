"""Tests for interacting with color interpretation."""

import pytest

import rasterio
from rasterio.enums import ColorInterp

from .conftest import requires_gdal22


def test_cmyk_interp(tmpdir):
    """A CMYK TIFF has cyan, magenta, yellow, black bands."""
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        meta = src.meta
    meta['photometric'] = 'CMYK'
    meta['count'] = 4
    tiffname = str(tmpdir.join('foo.tif'))
    with rasterio.open(tiffname, 'w', **meta) as dst:
        assert dst.profile['photometric'] == 'cmyk'
        assert dst.colorinterp == (
            ColorInterp.cyan,
            ColorInterp.magenta,
            ColorInterp.yellow,
            ColorInterp.black)


@requires_gdal22  # Some versions prior to 2.2.2 segfault on a Mac OSX Homebrew GDAL
def test_ycbcr_interp(tmpdir):
    """A YCbCr TIFF has red, green, blue bands."""
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        meta = src.meta
    meta['photometric'] = 'ycbcr'
    meta['compress'] = 'jpeg'
    meta['count'] = 3
    tiffname = str(tmpdir.join('foo.tif'))
    with rasterio.open(tiffname, 'w', **meta) as dst:
        assert dst.colorinterp == (
            ColorInterp.red, ColorInterp.green, ColorInterp.blue)


@pytest.mark.parametrize("dtype", [rasterio.ubyte, rasterio.int16])
def test_set_colorinterp(path_rgba_byte_tif, tmpdir, dtype):

    """Test setting color interpretation by creating an image without CI
    and then setting to unusual values.  Also test with a non-uint8 image.
    """

    no_ci_path = str(tmpdir.join('no-ci.tif'))
    with rasterio.open(path_rgba_byte_tif) as src:
        meta = src.meta.copy()
        meta.update(
            height=10,
            width=10,
            dtype=dtype,
            photometric='minisblack',
            alpha='unspecified')
    with rasterio.open(no_ci_path, 'w', **meta):
        pass

    # This is should be the default color interpretation of the copied
    # image.  GDAL defines these defaults, not Rasterio.
    src_ci = (
        ColorInterp.gray,
        ColorInterp.undefined,
        ColorInterp.undefined,
        ColorInterp.undefined)

    dst_ci = (
        ColorInterp.alpha,
        ColorInterp.blue,
        ColorInterp.green,
        ColorInterp.red)

    with rasterio.open(no_ci_path, 'r+') as src:
        assert src.colorinterp == src_ci
        src.colorinterp = dst_ci

    # See note in 'test_set_colorinterp_undefined'.  Opening a second
    # time catches situations like that.
    with rasterio.open(no_ci_path) as src:
        assert src.colorinterp == dst_ci


@pytest.mark.parametrize("ci", ColorInterp.__members__.values())
def test_set_colorinterp_all(path_4band_no_colorinterp, ci):

    """Test setting with all color interpretations."""

    with rasterio.open(path_4band_no_colorinterp, 'r+') as src:
        all_ci = list(src.colorinterp)
        all_ci[1] = ci
        src.colorinterp = all_ci

    with rasterio.open(path_4band_no_colorinterp) as src:
        assert src.colorinterp[1] == ci

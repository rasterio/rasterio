"""Tests for interacting with color interpretation."""


from collections import OrderedDict
import os

import pytest

import rasterio
from rasterio.enums import ColorInterp


def test_cmyk_interp(tmpdir):
    """A CMYK TIFF has cyan, magenta, yellow, black bands."""
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        meta = src.meta
    meta['photometric'] = 'CMYK'
    meta['count'] = 4
    tiffname = str(tmpdir.join('foo.tif'))
    with rasterio.open(tiffname, 'w', **meta) as dst:
        assert dst.profile['photometric'] == 'cmyk'
        dst.colorinterp = [
            ColorInterp.cyan,
            ColorInterp.magenta,
            ColorInterp.yellow,
            ColorInterp.black]


@pytest.mark.skipif(
    os.environ.get('TRAVIS', os.environ.get('CI', 'false')).lower() != 'true',
    reason="Crashing on OS X with Homebrew's GDAL")
def test_ycbcr_interp(tmpdir):
    """A YCbCr TIFF has red, green, blue bands."""
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        meta = src.meta
    meta['photometric'] = 'ycbcr'
    meta['compress'] = 'jpeg'
    meta['count'] = 3
    tiffname = str(tmpdir.join('foo.tif'))
    with rasterio.open(tiffname, 'w', **meta) as dst:
        dst.colorinterp = [
            ColorInterp.red, ColorInterp.green, ColorInterp.blue]


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
    src_ci_map = OrderedDict((
        (1, ColorInterp.gray),
        (2, ColorInterp.undefined),
        (3, ColorInterp.undefined),
        (4, ColorInterp.undefined)))

    dst_ci_map = OrderedDict((
        (1, ColorInterp.alpha),
        (2, ColorInterp.blue),
        (3, ColorInterp.green),
        (4, ColorInterp.red)))

    with rasterio.open(no_ci_path, 'r+') as src:
        ci_mapping = OrderedDict(zip(src.indexes, src.colorinterp))
        for bidx, ci in src_ci_map.items():
            assert ci_mapping[bidx] == ci
        src.colorinterp = dst_ci_map.values()

    # See note in 'test_set_colorinterp_undefined'.  Opening a second
    # time catches situations like that.
    with rasterio.open(no_ci_path) as src:
        ci_mapping = OrderedDict(zip(src.indexes, src.colorinterp))
        for bidx, ci in dst_ci_map.items():
            assert ci_mapping[bidx] == ci


@pytest.mark.parametrize("ci", ColorInterp.__members__.values())
def test_set_colorinterp_all(path_4band_no_colorinterp, ci):

    """Test setting with all color interpretations."""

    with rasterio.open(path_4band_no_colorinterp, 'r+') as src:
        all_ci = src.colorinterp
        all_ci[1] = ci
        src.colorinterp = all_ci

    with rasterio.open(path_4band_no_colorinterp) as src:
        assert src.colorinterp[1] == ci

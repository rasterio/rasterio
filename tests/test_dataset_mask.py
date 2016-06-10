import logging
import sys

import numpy as np
import pytest

from affine import Affine
import rasterio
from rasterio.enums import MaskFlags
from rasterio.errors import NodataShadowWarning
from rasterio.crs import CRS

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


# Setup test arrays
red = np.array([[0, 0, 0],
                [0, 1, 1],
                [1, 0, 1]]).astype('uint8') * 255

grn = np.array([[0, 0, 0],
                [1, 0, 1],
                [1, 0, 1]]).astype('uint8') * 255

blu = np.array([[0, 0, 0],
                [1, 1, 0],
                [1, 0, 1]]).astype('uint8') * 255

# equivalent to alp = red | grn | blu
# valid data anywhere there is at least one R, G or B value
alp = np.array([[0, 0, 0],
                [1, 1, 1],
                [1, 0, 1]]).astype('uint8') * 255

# mask might be constructed using different tools
# and differ from a strict interpretation of rgb values
msk = np.array([[0, 0, 0],
                [1, 1, 1],
                [1, 1, 1]]).astype('uint8') * 255

alldata = np.array([[1, 1, 1],
                    [1, 1, 1],
                    [1, 1, 1]]).astype('uint8') * 255

# boundless window ((1, 4, (1, 4))
alp_shift_lr = np.array([[1, 1, 0],
                         [0, 1, 0],
                         [0, 0, 0]]).astype('uint8') * 255

@pytest.fixture(scope='function')
def tiffs(tmpdir):

    _profile = {
        'affine': Affine(5.0, 0.0, 0.0, 0.0, -5.0, 0.0),
        'transform': Affine(5.0, 0.0, 0.0, 0.0, -5.0, 0.0),
        'crs': CRS({'init': 'epsg:4326'}),
        'driver': 'GTiff',
        'dtype': 'uint8',
        'height': 3,
        'width': 3}

    # 1. RGB without nodata value
    prof = _profile.copy()
    prof['count'] = 3
    prof['nodata'] = None
    with rasterio.open(str(tmpdir.join('rgb_no_ndv.tif')), 'w', **prof) as dst:
        dst.write(red, 1)
        dst.write(grn, 2)
        dst.write(blu, 3)

    # 2. RGB with nodata value
    prof = _profile.copy()
    prof['count'] = 3
    prof['nodata'] = 0
    with rasterio.open(str(tmpdir.join('rgb_ndv.tif')), 'w', **prof) as dst:
        dst.write(red, 1)
        dst.write(grn, 2)
        dst.write(blu, 3)

    # 3. RGBA without nodata value
    prof = _profile.copy()
    prof['count'] = 4
    prof['nodata'] = None
    with rasterio.open(str(tmpdir.join('rgba_no_ndv.tif')), 'w', **prof) as dst:
        dst.write(red, 1)
        dst.write(grn, 2)
        dst.write(blu, 3)
        dst.write(alp, 4)

    # 4. RGBA with nodata value
    prof = _profile.copy()
    prof['count'] = 4
    prof['nodata'] = 0
    with rasterio.open(str(tmpdir.join('rgba_ndv.tif')), 'w', **prof) as dst:
        dst.write(red, 1)
        dst.write(grn, 2)
        dst.write(blu, 3)
        dst.write(alp, 4)

    # 5. RGB with msk
    prof = _profile.copy()
    prof['count'] = 3
    with rasterio.open(str(tmpdir.join('rgb_msk.tif')), 'w', **prof) as dst:
        dst.write(red, 1)
        dst.write(grn, 2)
        dst.write(blu, 3)
        dst.write_mask(msk)

    # 6. RGB with msk (internal)
    prof = _profile.copy()
    prof['count'] = 3
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True) as env:
        with rasterio.open(str(tmpdir.join('rgb_msk_internal.tif')),
                           'w', **prof) as dst:
            dst.write(red, 1)
            dst.write(grn, 2)
            dst.write(blu, 3)
            dst.write_mask(msk)

    # 7. RGBA with msk
    prof = _profile.copy()
    prof['count'] = 4
    with rasterio.open(str(tmpdir.join('rgba_msk.tif')), 'w', **prof) as dst:
        dst.write(red, 1)
        dst.write(grn, 2)
        dst.write(blu, 3)
        dst.write(alp, 4)
        dst.write_mask(msk)

    return tmpdir


def test_no_ndv(tiffs):
    with rasterio.open(str(tiffs.join('rgb_no_ndv.tif'))) as src:
        assert np.array_equal(src.dataset_mask(), alldata)

def test_rgb_ndv(tiffs):
    with rasterio.open(str(tiffs.join('rgb_ndv.tif'))) as src:
        assert np.array_equal(src.dataset_mask(), alp)

def test_rgba_no_ndv(tiffs):
    with rasterio.open(str(tiffs.join('rgba_no_ndv.tif'))) as src:
        assert np.array_equal(src.dataset_mask(), alp)

def test_rgba_ndv(tiffs):
    with rasterio.open(str(tiffs.join('rgba_ndv.tif'))) as src:
        with pytest.warns(NodataShadowWarning):
            res = src.dataset_mask()
        assert np.array_equal(res, alp)

def test_rgb_msk(tiffs):
    with rasterio.open(str(tiffs.join('rgb_msk.tif'))) as src:
        assert np.array_equal(src.dataset_mask(), msk)
        # each band's mask is also equal
        for bmask in src.read_masks():
            assert np.array_equal(bmask, msk)

def test_rgb_msk_int(tiffs):
    with rasterio.open(str(tiffs.join('rgb_msk_internal.tif'))) as src:
        assert np.array_equal(src.dataset_mask(), msk)

def test_rgba_msk(tiffs):
    with rasterio.open(str(tiffs.join('rgba_msk.tif'))) as src:
        # mask takes precendent over alpha
        assert np.array_equal(src.dataset_mask(), msk)

def test_kwargs(tiffs):
    with rasterio.open(str(tiffs.join('rgb_ndv.tif'))) as src:
        # window and boundless are passed along
        other = src.dataset_mask(window=((1, 4), (1, 4)), boundless=True)
        assert np.array_equal(alp_shift_lr, other)

        # band indexes are not supported
        with pytest.raises(TypeError):
            src.dataset_mask(indexes=1)

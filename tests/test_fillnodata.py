import logging
import sys

import numpy as np
import pytest

import rasterio
from rasterio.fill import fillnodata


@pytest.fixture(scope='session')
def hole_in_ones():
    """A 5x5 array with one nodata pixel dead center"""
    a = np.ones((5, 5), dtype='uint8')
    a[2][2] = 0
    return a


def test_fillnodata(hole_in_ones):
    """Test filling nodata values in an ndarray"""
    mask = hole_in_ones == 1
    result = fillnodata(hole_in_ones, mask)
    assert (result == 1).all()


def test_fillnodata_masked_array(hole_in_ones):
    """Test filling nodata values in a masked ndarray"""
    ma = np.ma.masked_array(hole_in_ones, (hole_in_ones == 0))
    result = fillnodata(ma)
    assert (result == 1).all()


def test_fillnodata_invalid_types():
    a = np.ones([3, 3])
    with pytest.raises(ValueError):
        fillnodata(None, a)
    with pytest.raises(ValueError):
        fillnodata(a, 42)


def test_fillnodata_mask_ones(hole_in_ones):
    """when mask is all ones, image should be unmodified"""
    mask = np.ones((5, 5))
    result = fillnodata(hole_in_ones, mask)
    assert(np.all(hole_in_ones == result))

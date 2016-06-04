import logging
import sys

import numpy as np
import pytest

import rasterio
from rasterio.fill import fillnodata

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

def test_fillnodata():
    """Test filling nodata values in an ndarray"""
    # create a 5x5 array, with some missing data
    a = np.ones([3, 3]) * 42
    a[1][1] = 0
    # find the missing data
    mask = ~(a == 0)
    # fill the missing data using interpolation from the edges
    result = fillnodata(a, mask)
    assert(np.all((np.ones([3, 3]) * 42) == result))

def test_fillnodata_invalid_types():
    a = np.ones([3, 3])
    with pytest.raises(ValueError):
        fillnodata(None, a)
    with pytest.raises(ValueError):
        fillnodata(a, 42)

def test_fillnodata_mask_ones():
    # when mask is all ones, image should be unmodified
    a = np.ones([3, 3]) * 42
    a[1][1] = 0
    mask = np.ones([3, 3])
    result = fillnodata(a, mask)
    assert(np.all(a == result))

'''
def test_fillnodata_smooth():
    a = np.array([[1,3,3,1],[2,0,0,2],[2,0,0,2],[1,3,3,1]], dtype=np.float64)
    mask = ~(a == 0)
    result = fillnodata(a, mask, max_search_distance=1, smoothing_iterations=0)
    assert(result[1][1] == 3)
    result = fillnodata(a, mask, max_search_distance=1, smoothing_iterations=1)
    assert(round(result[1][1], 1) == 2.2)
'''

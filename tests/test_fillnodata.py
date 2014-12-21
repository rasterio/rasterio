import logging
import sys
import numpy
import pytest

import rasterio
from rasterio.fill import fillnodata

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

def test_fillnodata():
    """Test filling nodata values in an ndarray"""
    # create a 5x5 array, with some missing data
    a = numpy.ones([5, 5]) * 42
    a[1:4,1:4] = numpy.nan
    # find the missing data
    mask = ~numpy.isnan(a)
    # fill the missing data using interpolation from the edges
    ret = fillnodata(a, mask)
    assert(((numpy.ones([5, 5]) * 42) - a).sum() == 0)
    assert(ret is None) # inplace modification, should not return anything

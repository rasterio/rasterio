import logging
import sys
import uuid

import numpy as np
import pytest

import rasterio


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


@pytest.fixture(scope='function')
def tempfile():
    """A temporary filename in the GDAL '/vsimem' filesystem"""
    return '/vsimem/{}'.format(uuid.uuid4())


def complex_image(height, width, dtype):
    """An array with sequential elements"""
    return np.array(
        [complex(x, x) for x in range(height * width)],
        dtype=dtype).reshape(height, width)

dtypes = ['complex', 'complex64', 'complex128']


@pytest.mark.parametrize("dtype", dtypes)
@pytest.mark.parametrize("height,width", [(20, 20)])
def test_read_array(tempfile, dtype, height, width):
    """_io functions read and write arrays correctly"""
    in_img = complex_image(height, width, dtype)
    with rasterio.open(tempfile, 'w+', driver='GTiff', dtype=dtype,
                       height=height, width=width, count=1) as dataset:
        dataset.write(in_img, 1)
        out_img = dataset.read(1)
    assert (in_img == out_img).all()

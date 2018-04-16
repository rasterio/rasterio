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


def image(height, width, dtype):
    """An array with sequential elements"""
    return np.array(range(height * width), dtype=dtype).reshape(height, width)


dtypes = ['uint8', 'uint16', 'int16', 'uint32', 'int32', 'float32', 'float64']

@pytest.mark.parametrize("dtype", dtypes)
@pytest.mark.parametrize("height,width", [(20, 30)])
def test_read_array(tempfile, dtype, height, width):
    """_io functions read and write arrays correctly"""
    in_img = image(height, width, dtype)
    with rasterio.open(tempfile, 'w+', driver='GTiff', dtype=dtype,
                       height=height, width=width, count=1) as dataset:
        dataset.write(in_img, 1)
        out_img = dataset.read(1)
    assert (in_img == out_img).all()


@pytest.mark.parametrize("dtype", dtypes)
@pytest.mark.parametrize("height,width", [(20, 30)])
def test_read_view_no_offset(tempfile, dtype, height, width):
    """_io functions read views with no offset correctly"""
    in_img = image(height, width, dtype)
    with rasterio.open(tempfile, 'w+', driver='GTiff', dtype=dtype,
                       height=10, width=15, count=1) as dataset:
        dataset.write(in_img[:10, :15], 1)
        out_img = dataset.read(1)
    assert (in_img[:10, :15] == out_img).all()


@pytest.mark.parametrize("dtype", dtypes)
@pytest.mark.parametrize("height,width", [(20, 30)])
def test_read_view_offset(tempfile, dtype, height, width):
    """_io functions read views with offsets correctly"""
    in_img = image(height, width, dtype)
    with rasterio.open(tempfile, 'w+', driver='GTiff', dtype=dtype,
                       height=10, width=15, count=1) as dataset:
        dataset.write(in_img[5:15, 5:20], 1)
        out_img = dataset.read(1)
    assert (in_img[5:15, 5:20] == out_img).all()


@pytest.mark.parametrize("dtype", dtypes)
@pytest.mark.parametrize("height,width", [(20, 30)])
def test_write_view_no_offset(tempfile, dtype, height, width):
    """_io functions read views without offsets correctly"""
    out_img = image(height, width, dtype)
    in_img = np.zeros((10, 10), dtype=dtype)
    with rasterio.open(tempfile, 'w+', driver='GTiff', dtype=dtype,
                       height=10, width=10, count=1) as dataset:
        dataset.write(in_img, 1)
    with rasterio.open(tempfile) as dataset:
        result = dataset.read(1, out=out_img[:10, :10])

    assert (result == 0).all()
    assert (out_img[:10, :10] == 0).all()


@pytest.mark.parametrize("dtype", dtypes)
@pytest.mark.parametrize("height,width", [(20, 30)])
def test_write_view_offset(tempfile, dtype, height, width):
    """_io functions read views with offsets correctly"""
    out_img = np.ones((height, width), dtype=dtype)
    in_img = np.zeros((10, 10), dtype=dtype)
    with rasterio.open(tempfile, 'w+', driver='GTiff', dtype=dtype,
                       height=10, width=10, count=1) as dataset:
        dataset.write(in_img, 1)
    with rasterio.open(tempfile) as dataset:
        result = dataset.read(1, out=out_img[5:15, 5:15])

    assert (result == 0).all()
    assert (out_img[5:15, 5:15] == 0).all()
    assert (out_img[:5, :5] == 1).all()
    assert (out_img[15:, 15:] == 1).all()

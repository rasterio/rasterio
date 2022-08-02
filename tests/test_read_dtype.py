"""Tests of out_dtype in read()"""

import itertools

import affine
import numpy
import pytest

import rasterio
from rasterio import (
    ubyte,
    uint8,
    uint16,
    uint32,
    uint64,
    sbyte,
    int8,
    int16,
    int32,
    int64,
    float32,
    float64,
    complex_,
    complex_int16,
)
from rasterio.env import GDALVersion


_GDAL_AT_LEAST_35 = GDALVersion.runtime().at_least("3.5")

DTYPES = [
    ubyte,
    uint8,
    uint16,
    uint32,
    sbyte,
    int8,
    int16,
    int32,
    float32,
    float64,
    complex_,
]

if _GDAL_AT_LEAST_35:
    DTYPES.extend([uint64, int64])


def test_uint8_default(path_rgb_byte_tif):
    """Get uint8 array from uint8 dataset"""
    with rasterio.open(path_rgb_byte_tif) as dataset:
        assert dataset.read().dtype == numpy.dtype('uint8')


def test_uint8_to_float32(path_rgb_byte_tif):
    """Get float32 array from uint8 dataset"""
    with rasterio.open(path_rgb_byte_tif) as dataset:
        assert dataset.read(out_dtype='float32').dtype == numpy.dtype('float32')


def test_uint8_to_float32_out_param(path_rgb_byte_tif):
    """Get float32 array from uint8 dataset via out parameter"""
    with rasterio.open(path_rgb_byte_tif) as dataset:
        assert dataset.read(out=numpy.zeros((dataset.count, dataset.height, dataset.width), dtype='float32')).dtype == numpy.dtype('float32')


def test_float32_to_int16():
    """Get int16 array from float32 dataset"""
    with rasterio.open('tests/data/float_nan.tif') as dataset:
        data = dataset.read(out_dtype='int16')

    assert data.dtype == numpy.dtype('int16')
    assert (data == numpy.array([[[ 1,  1,  0], [ 0,  0, -2]]], dtype='int16')).all()


@pytest.mark.parametrize("dtype,nodata", itertools.product(DTYPES, [1, 127]))
def test_write_mem(dtype, nodata):
    profile = {
        "driver": "GTiff",
        "width": 2,
        "height": 1,
        "count": 1,
        "dtype": dtype,
        "crs": "EPSG:3857",
        "transform": affine.Affine(10, 0, 0, 0, -10, 0),
        "nodata": nodata,
    }

    values = numpy.array([[nodata, nodata]], dtype=dtype)

    with rasterio.open("/vsimem/test.tif", "w", **profile) as src:
        src.write(values, indexes=1)

    with rasterio.open("/vsimem/test.tif") as src:
        read = src.read(indexes=1)
        assert read[0][0] == nodata
        assert read[0][1] == nodata


@pytest.mark.parametrize("dtype,nodata", itertools.product(DTYPES, [None, 1, 127]))
def test_write_fs(tmp_path, dtype, nodata):
    filename = tmp_path.joinpath("test.tif")
    profile = {
        "driver": "GTiff",
        "width": 2,
        "height": 1,
        "count": 1,
        "dtype": dtype,
        "crs": "EPSG:3857",
        "transform": affine.Affine(10, 0, 0, 0, -10, 0),
        "nodata": nodata,
    }

    if dtype.startswith('int') or dtype.startswith('uint'):
        info = numpy.iinfo(dtype)
    else:
        info = numpy.finfo(dtype)
    values = numpy.array([[info.max, info.min]], dtype=dtype)

    with rasterio.open(filename, "w", **profile) as src:
        src.write(values, indexes=1)

    with rasterio.open(filename) as src:
        read = src.read(indexes=1)
        assert read[0][0] == info.max
        assert read[0][1] == info.min

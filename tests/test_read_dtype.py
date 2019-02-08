"""Tests of out_dtype in read()"""

import numpy

import rasterio


def test_uint8_default(path_rgb_byte_tif):
    """Get uint8 array from uint8 dataset"""
    with rasterio.open(path_rgb_byte_tif) as dataset:
        assert dataset.read().dtype == numpy.dtype('uint8')


def test_uint8_to_float32(path_rgb_byte_tif):
    """Get float32 array from uint8 dataset"""
    with rasterio.open(path_rgb_byte_tif) as dataset:
        assert dataset.read(out_dtype='float32').dtype == numpy.dtype('float32')


def test_float32_to_int16():
    """Get int16 array from float32 dataset"""
    with rasterio.open('tests/data/float_nan.tif') as dataset:
        data = dataset.read(out_dtype='int16')

    assert data.dtype == numpy.dtype('int16')
    assert (data == numpy.array([[[ 1,  1,  0], [ 0,  0, -2]]], dtype='int16')).all()


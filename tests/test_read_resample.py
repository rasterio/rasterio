"""
Rasterio exposes GDAL's resampling/decimation on I/O. These are the tests
that it does this correctly.
"""

import numpy as np
import pytest

import rasterio
from rasterio.enums import Resampling
from rasterio.errors import ResamplingAlgorithmError
from rasterio.windows import Window

from .conftest import requires_gdal33


# Rasterio's test dataset is 718 rows by 791 columns.

def test_read_out_shape_resample_down():
    with rasterio.open('tests/data/RGB.byte.tif') as s:
        out = np.zeros((8, 8), dtype=rasterio.ubyte)
        data = s.read(1, out=out)
        expected = np.array([
            [  0,   0,  20,  15,   0,   0,   0,   0],
            [  0,   6, 193,   9, 255, 127,  23,  39],
            [  0,   7,  27, 255, 193,  14,  28,  34],
            [  0,  31,  29,  44,  14,  22,  43,   0],
            [  0,   9,  69,  49,  17,  22, 255,   0],
            [ 11,   7,  13,  25,  13,  29,  33,   0],
            [  8,  10,  88,  27,  20,  33,  25,   0],
            [  0,   0,   0,   0,  98,  23,   0,   0]], dtype=np.uint8)
        assert (data == expected).all()  # all True.


def test_read_out_shape_resample_up():
    # Instead of testing array items, test statistics. Upsampling by an even
    # constant factor shouldn't change the mean.
    with rasterio.open('tests/data/RGB.byte.tif') as s:
        out = np.zeros((7180, 7910), dtype=rasterio.ubyte)
        data = s.read(1, out=out, masked=True)
        assert data.shape == (7180, 7910)
        assert data.mean() == s.read(1, masked=True).mean()


# TODO: justify or remove this test.
def test_read_downsample_alpha():
    with rasterio.Env(GTIFF_IMPLICIT_JPEG_OVR=False):
        with rasterio.open('tests/data/alpha.tif') as src:
            out = np.zeros((100, 100), dtype=rasterio.ubyte)
            assert src.width == 1223
            assert src.height == 1223
            assert src.count == 4
            assert src.read(1, out=out, masked=False).shape == out.shape
            # attempt decimated read of alpha band
            src.read(4, out=out, masked=False)


def test_resample_alg_effect_1():
    """default (nearest) and cubic produce different results"""
    with rasterio.open('tests/data/RGB.byte.tif') as s:
        # Existence of overviews can upset our expectations, so we
        # guard against that here.
        assert not any([s.overviews(bidx) for bidx in s.indexes])
        out_shape = (s.height // 2, s.width // 2)
        nearest = s.read(1, out_shape=out_shape)
        cubic = s.read(1, out_shape=out_shape, resampling=Resampling.cubic)
        assert np.any(nearest != cubic)


def test_resample_alg_effect_2():
    """Average and bilinear produce different results"""
    with rasterio.open('tests/data/RGB.byte.tif') as s:
        # Existence of overviews can upset our expectations, so we
        # guard against that here.
        assert not any([s.overviews(bidx) for bidx in s.indexes])
        out_shape = (s.height // 2, s.width // 2)
        avg = s.read(1, out_shape=out_shape, resampling=Resampling.average)
        bilin = s.read(1, out_shape=out_shape, resampling=Resampling.bilinear)
        assert np.any(avg != bilin)


def test_float_window():
    """floating point windows work"""
    with rasterio.open('tests/data/RGB.byte.tif') as s:
        out_shape = (401, 401)
        window = Window(300.5, 300.5, 200.5, 200.5)
        s.read(1, window=window, out_shape=out_shape)


def test_resampling_alg_error():
    """Get an exception instead of a crash when using warp-only algs for read or write, see issue #1930"""
    with pytest.raises(ResamplingAlgorithmError):
        with rasterio.open("tests/data/RGB.byte.tif") as src:
            src.read(1, out_shape=(1, 10, 10), resampling=Resampling.max)


@requires_gdal33
def test_resampling_rms():
    """Test Resampling.rms method"""
    with rasterio.open('tests/data/float.tif') as s:
        out_shape = (2, 2)
        rms = s.read(1, out_shape=out_shape, resampling=Resampling.rms)
        expected = np.array([
            [1.35266399, 0.95388681],
            [0.29308701, 1.54074657]], dtype=np.float32)
        assert (rms == expected).all()  # all True.

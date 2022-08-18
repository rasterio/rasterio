import numpy

import rasterio


def test_sampling():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = next(src.sample([(220650.0, 2719200.0)]))
        assert list(data) == [18, 25, 14]


def test_sampling_beyond_bounds():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = next(src.sample([(-10, 2719200.0)]))
        assert list(data) == [0, 0, 0]


def test_sampling_beyond_bounds_no_nodata():
    with rasterio.open('tests/data/RGB2.byte.tif') as src:
        data = next(src.sample([(-10, 2719200.0)]))
        assert list(data) == [0, 0, 0]


def test_sampling_beyond_bounds_masked():
    with rasterio.open('tests/data/RGBA.byte.tif') as src:
        data = next(src.sample([(-10, 2719200.0)], masked=True))
        assert list(data.mask) == [True, True, True, False]


def test_sampling_beyond_bounds_nan():
    with rasterio.open('tests/data/float_nan.tif') as src:
        data = next(src.sample([(-10, 0.0)]))
        assert numpy.isnan(data)


def test_sampling_indexes():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = next(src.sample([(220650.0, 2719200.0)], indexes=[2]))
        assert list(data) == [25]


def test_sampling_single_index():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = next(src.sample([(220650.0, 2719200.0)], indexes=2))
        assert list(data) == [25]


def test_sampling_type():
    """See https://github.com/rasterio/rasterio/issues/378."""
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        sampler = src.sample([(220650.0, 2719200.0)], indexes=[2])
        assert type(sampler)


def test_sampling_ndarray():
    """sample and sample_gen can take ndarrays of coords."""
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = next(src.sample(numpy.array([[220650.0, 2719200.0]])))
        assert list(data) == [18, 25, 14]

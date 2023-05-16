import numpy

import rasterio


def test_sampling():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = next(src.sample([(220650.0, 2719200.0)]))
        assert list(data) == [18, 25, 14]


def test_sampling_beyond_bounds():
    """Unmasked sampling beyond bounds yields unmasked array of zeros."""
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = next(src.sample([(0.0, 0.0)]))
        assert not numpy.ma.is_masked(data)
        assert list(data) == [0, 0, 0]


def test_sampling_masked_beyond_bounds():
    """Masked sampling beyond bounds yields an entirely masked array."""
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        data = next(src.sample([(0.0, 0.0)], masked=True))
        assert numpy.ma.is_masked(data)
        assert all(data.mask == True)


def test_sampling_no_nodata_masked_beyond_bounds(data):
    """Masked sampling beyond bounds yields an entirely masked array."""
    filename = str(data.join("RGB.byte.tif"))

    with rasterio.open(filename, "r+") as src:
        src.nodata = None

    with rasterio.open(filename) as src:
        data = next(src.sample([(0.0, 0.0)], masked=True))
        assert numpy.ma.is_masked(data)
        assert all(data.mask == True)


def test_sampling_beyond_bounds_no_nodata_masked():
    """Masked sampling beyond bounds yields an entirely masked array."""
    with rasterio.open('tests/data/RGB2.byte.tif') as src:
        data = next(src.sample([(0.0, 0.0)], masked=True))
        assert all(data.mask == True)


def test_sampling_beyond_bounds_masked():
    """Masked sampling beyond bounds yields a masked array with last element being False."""
    with rasterio.open('tests/data/RGBA.byte.tif') as src:
        data = next(src.sample([(0.0, 0.0)], masked=True))
        assert list(data.mask) == [True, True, True, False]


def test_sampling_beyond_bounds_nan():
    with rasterio.open('tests/data/float_nan.tif') as src:
        data = next(src.sample([(-10.0, 0.0)]))
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

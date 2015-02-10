import rasterio


def test_sampling():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = next(src.sample([(220650.0, 2719200.0)]))
        assert list(data) == [28, 29, 27]

def test_sampling_beyond_bounds():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = next(src.sample([(-10, 2719200.0)]))
        assert list(data) == [0, 0, 0]

def test_sampling_indexes():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = next(src.sample([(220650.0, 2719200.0)], indexes=[2]))
        assert list(data) == [29]

# Tests of dataset meta keywords and dataset creation

import rasterio


def test_copy_meta(tmpdir):
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        kwds = src.meta
    with rasterio.open(
            str(tmpdir.join('test_copy_meta.tif')), 'w', **kwds) as dst:
        assert dst.meta['count'] == 3


def test_blacklisted_keys(tmpdir):
    # Some keys were removed from .meta when they were found to clash with
    # creation options.
    # https://github.com/rasterio/rasterio/issues/402
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        kwds = src.meta
    with rasterio.open(
            str(tmpdir.join('test_copy_meta.tif')), 'w', **kwds) as dst:
        keys = map(lambda x: x.lower(), dst.meta.keys())
        assert 'blockxsize' not in keys
        assert 'blockysize' not in keys
        assert 'tiled' not in keys

# Tests of dataset meta keywords and dataset creation

import rasterio


def test_blocksize_rgb(tmpdir):
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        kwds = src.meta
        assert kwds['blockxsize'] == 791
        assert kwds['blockysize'] == 3
        assert kwds['tiled'] is False

def test_blocksize_shade(tmpdir):
    with rasterio.open('tests/data/shade.tif') as src:
        kwds = src.meta
        assert kwds['blockxsize'] == 1024
        assert kwds['blockysize'] == 8
        assert kwds['tiled'] is False

def test_copy_meta(tmpdir):
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        kwds = src.meta
    with rasterio.open(
            str(tmpdir.join('test_copy_meta.tif')), 'w', **kwds) as dst:
        assert dst.meta['count'] == 3
        assert dst.meta['blockxsize'] == 791
        assert dst.meta['blockysize'] == 3
        assert dst.meta['tiled'] is False

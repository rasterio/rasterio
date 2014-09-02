import rasterio

def test_band():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        b = rasterio.band(src, 1)
        assert b.ds == src
        assert b.bidx == 1
        assert b.dtype in src.dtypes
        assert b.shape == src.shape


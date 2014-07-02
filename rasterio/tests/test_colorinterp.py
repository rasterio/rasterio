import rasterio

def test_colorinterp():
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        assert src.colorinterp(1) == 3
        assert src.colorinterp(2) == 4
        assert src.colorinterp(3) == 5


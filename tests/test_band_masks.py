import rasterio


def test_masks():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        m = src.read_mask()
        r, g, b = src.read()
        assert r[m==0].mask.all()
        # The following fails because m isn't the proper mask for g (band 2).
        assert g[m==0].mask.all()

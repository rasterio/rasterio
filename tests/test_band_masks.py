import rasterio


def test_masks():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        rm, gm, bm = src.read_masks()
        r, g, b = src.read(masked=False)
        assert not r[rm==0].any()
        assert not g[gm==0].any()
        assert not b[bm==0].any()

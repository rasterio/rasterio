import rasterio


def test_subdatasets():
    with rasterio.open('netcdf:tests/data/RGB.nc') as src:
        subs = src.subdatasets()
        assert len(subs) == 3
        for sub in subs:
            assert 'name' in sub
            assert 'description' in sub

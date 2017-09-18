import pytest

import rasterio


@pytest.mark.skipif(rasterio.__gdal_version__.startswith('1.9') or
                    rasterio.__gdal_version__.startswith('2.0'),
                    reason="netcdf driver not available before GDAL 2.1")
def test_subdatasets():
    """Get subdataset names and descriptions"""
    with rasterio.open('netcdf:tests/data/RGB.nc') as src:
        subs = src.subdatasets()
        assert len(subs) == 3
        for sub in subs:
            assert 'name' in sub
            assert 'description' in sub

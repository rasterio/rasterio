from packaging.version import parse
import pytest

import rasterio


@pytest.mark.skipif(parse(rasterio.__gdal_version__) < parse('2.1'),
                    reason="netcdf driver not available before GDAL 2.1")
def test_subdatasets():
    """Get subdataset names and descriptions"""
    with rasterio.open('netcdf:tests/data/RGB.nc') as src:
        subs = src.subdatasets
        assert len(subs) == 3
        for name in subs:
            assert name.startswith('netcdf')

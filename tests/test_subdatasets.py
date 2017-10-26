from packaging.version import parse
import pytest

import rasterio


with rasterio.Env() as env:
    HAVE_NETCDF = 'NetCDF' in env.drivers().keys()


@pytest.mark.skipif(parse(rasterio.__gdal_version__) < parse('2.1'),
                    reason="netcdf driver not available before GDAL 2.1")
@pytest.mark.skipif(not HAVE_NETCDF,
                    reason="GDAL not compiled with NetCDF driver.")
def test_subdatasets():
    """Get subdataset names and descriptions"""
    with rasterio.open('netcdf:tests/data/RGB.nc') as src:
        subs = src.subdatasets
        assert len(subs) == 3
        for name in subs:
            assert name.startswith('netcdf')

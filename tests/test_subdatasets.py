import pytest

import rasterio

from .conftest import requires_gdal21

with rasterio.Env() as env:
    HAVE_NETCDF = 'NetCDF' in env.drivers().keys()


@requires_gdal21  # NetCDF requires 2.1.x
@pytest.mark.skipif(not HAVE_NETCDF,
                    reason="GDAL not compiled with NetCDF driver.")
def test_subdatasets():
    """Get subdataset names and descriptions"""
    with rasterio.open('netcdf:tests/data/RGB.nc') as src:
        subs = src.subdatasets
        assert len(subs) == 3
        for name in subs:
            assert name.startswith('netcdf')

import pytest

import rasterio

with rasterio.Env() as env:
    HAVE_NETCDF = "netCDF" in env.drivers().keys()
    HAVE_HDF5 = "HDF5" in env.drivers().keys()


@pytest.mark.skipif(not HAVE_NETCDF, reason="GDAL not compiled with NetCDF driver.")
def test_subdatasets():
    """Get subdataset names and descriptions"""
    with rasterio.open("netcdf:tests/data/RGB.nc") as src:
        subs = src.subdatasets
        assert len(subs) == 3
        for name in subs:
            assert name.startswith("netcdf")


@pytest.mark.skipif(not HAVE_HDF5, reason="GDAL not compiled with HDF5 driver.")
def test_subdatasets_h5():
    """Get subdataset names and descriptions"""
    with rasterio.open("tests/data/two-subs.h5") as src:
        subs = src.subdatasets
        assert len(subs) == 2
        assert src.profile["count"] == 0

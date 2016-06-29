from rasterio.drivers import is_blacklisted


def test_netcdf_is_blacklisted():
    assert is_blacklisted('netCDF', 'w')
    assert is_blacklisted('netCDF', 'r+')


def test_gtiff_is_not_blacklisted():
    assert not is_blacklisted('GTiff', 'w')
    assert not is_blacklisted('GTiff', 'r+')

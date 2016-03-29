# Testing use of cpl_errs

import pytest

import rasterio
from rasterio.errors import RasterioIOError


def test_io_error(tmpdir):
    with pytest.raises(RasterioIOError) as exc_info:
        rasterio.open(str(tmpdir.join('foo.tif')))
    msg, = exc_info.value.args
    assert msg.startswith("'{0}'".format(tmpdir.join('foo.tif')))
    assert ("does not exist in the file system, and is not recognised as a "
            "supported dataset name.") in msg


def test_io_error_env(tmpdir):
    with rasterio.drivers() as env:
        drivers_start = env.drivers()
        with pytest.raises(RasterioIOError):
            rasterio.open(str(tmpdir.join('foo.tif')))
    assert env.drivers() == drivers_start


def test_bogus_band_error():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert src._has_band(4) is False

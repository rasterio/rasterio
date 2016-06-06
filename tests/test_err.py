# Testing use of cpl_errs

import pytest

import rasterio
from rasterio._err import CPLError
from rasterio.errors import RasterioIOError


def test_io_error(tmpdir):
    """RasterioIOError is raised when a disk file can't be opened.

    Newlines are removed from GDAL error messages.
    """
    with pytest.raises(RasterioIOError) as exc_info:
        rasterio.open(str(tmpdir.join('foo.tif')))
    msg, = exc_info.value.args
    assert "\n" not in msg


def test_io_error_env(tmpdir):
    with pytest.raises(RasterioIOError):
        rasterio.open(str(tmpdir.join('foo.tif')))


def test_bogus_band_error():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert src._has_band(4) is False


def test_cplerror_str():
    err = CPLError(1, 1, "test123")
    assert str(err) == "test123"

"""Tests for ``rasterio._manage.pyx```."""


import os

import pytest

import rasterio
from rasterio.errors import DriverRegistrationError, RasterioIOError


@pytest.mark.parametrize("driver", (None, 'GTiff'))
def test_delete(driver, path_rgb_byte_tif, tmpdir):

    """Delete a file with ``rasterio.delete()``.  Also specifies driver."""

    path = str(tmpdir.join('test_delete.tif'))
    rasterio.copy(path_rgb_byte_tif, path)
    assert os.path.exists(path)
    rasterio.delete(path, driver=driver)


def test_delete_invalid_path():

    """Invalid dataset."""

    with pytest.raises(RasterioIOError) as e:
        rasterio.delete('trash')
    assert 'Invalid dataset' in str(e)


def test_delete_invalid_driver(path_rgb_byte_tif, tmpdir):

    """Valid dataset and invalid driver."""

    path = str(tmpdir.join('test_invalid_driver.tif'))
    rasterio.copy(path_rgb_byte_tif, path)
    with pytest.raises(DriverRegistrationError) as e:
        rasterio.delete(path, driver='trash')
    assert 'Unrecognized driver' in str(e)


def test_exists(path_rgb_byte_tif):

    assert rasterio.exists(path_rgb_byte_tif)
    assert not rasterio.exists('trash')

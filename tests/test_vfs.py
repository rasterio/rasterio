import logging
import sys

import pytest

import rasterio
from rasterio.profiles import default_gtiff_profile


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_read_vfs_zip():
    with rasterio.open(
            'zip://tests/data/files.zip!/RGB.byte.tif') as src:
        assert src.name == 'zip://tests/data/files.zip!/RGB.byte.tif'
        assert src.count == 3


def test_read_vfs_file():
    with rasterio.open(
            'file://tests/data/RGB.byte.tif') as src:
        assert src.name == 'file://tests/data/RGB.byte.tif'
        assert src.count == 3


def test_read_vfs_none():
    with rasterio.open(
            'tests/data/RGB.byte.tif') as src:
        assert src.name == 'tests/data/RGB.byte.tif'
        assert src.count == 3


@pytest.mark.parametrize('mode', ['r+', 'w'])
def test_update_vfs(tmpdir, mode):
    """VFS datasets can not be created or updated"""
    with pytest.raises(TypeError):
        _ = rasterio.open(
            'zip://{0}'.format(tmpdir), mode,
            **default_gtiff_profile(
                count=1, width=1, height=1))

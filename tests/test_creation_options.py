"""Tests of creation option behavior"""

import logging

import rasterio
from rasterio.profiles import DefaultGTiffProfile


def test_warning(tmpdir, caplog):
    """Be warned about invalid creation options"""
    profile = DefaultGTiffProfile(
        count=1, height=256, width=256, compression="lolwut", foo="bar"
    )
    with caplog.at_level(logging.WARNING, logger="rasterio"):
        with rasterio.Env(GDAL_VALIDATE_CREATION_OPTIONS=True):
            rasterio.open(str(tmpdir.join("test.tif")), "w", **profile)
    assert caplog.record_tuples == [
        (
            "rasterio._env",
            logging.WARNING,
            "CPLE_NotSupported in driver GTiff does not support creation option COMPRESSION",
        ),
        (
            "rasterio._env",
            logging.WARNING,
            "CPLE_NotSupported in driver GTiff does not support creation option FOO",
        ),
    ]

"""Tests of creation option behavior"""

import logging

import rasterio
from rasterio.profiles import DefaultGTiffProfile

from .conftest import requires_gdal2


@requires_gdal2(reason="GDAL 1.x warning text is obsolete")
def test_warning(tmpdir, caplog):
    """Be warned about invalid creation options"""
    profile = DefaultGTiffProfile(
        count=1, height=256, width=256, compression="lolwut", foo="bar"
    )

    with rasterio.Env(GDAL_VALIDATE_CREATION_OPTIONS=True):
        rasterio.open(str(tmpdir.join("test.tif")), "w", **profile)

    assert [
        "CPLE_NotSupported in driver GTiff does not support creation option COMPRESSION",
        "CPLE_NotSupported in driver GTiff does not support creation option FOO",
    ] == sorted(
        [
            rec.message
            for rec in caplog.records
            if rec.levelno == logging.WARNING and rec.name == "rasterio._env"
        ]
    )

"""Testing related to GDAL CPLError handling."""

import pytest

import rasterio
from rasterio._err import CPLE_BaseError
from rasterio.errors import RasterioIOError


def test_io_error(tmpdir):
    """RasterioIOError is raised when a disk file can't be opened.
    Newlines are removed from GDAL error messages."""
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
    err = CPLE_BaseError(1, 1, "test123")
    assert str(err) == "test123"


def test_issue2353(caplog, path_rgb_byte_tif):
    """Ensure transformer doesn't leave errors behind."""
    from rasterio.warp import calculate_default_transform

    with rasterio.open(path_rgb_byte_tif) as src:
        _ = src.colorinterp
        t, w, h = calculate_default_transform(
            'PROJCS["unknown",GEOGCS["unknown",DATUM["unknown",SPHEROID["GRS 1980",6378137,298.257222096042]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433]],PROJECTION["Geostationary_Satellite"],PARAMETER["central_meridian",-137],PARAMETER["satellite_height",35786023],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH],EXTENSION["PROJ4","+proj=geos +sweep=x +lon_0=-137 +h=35786023 +x_0=0 +y_0=0 +ellps=GRS80 +units=m +no_defs"]]',
            "EPSG:4326",
            21696,
            21696,
            -5434894.885056,
            -5434894.885056,
            5434894.885056,
            5434894.885056,
        )
        assert "Ignoring error" in caplog.text
        _ = src.colorinterp


def test_issue2353bis(caplog, path_rgb_byte_tif):
    """Ensure VRT doesn't leave errors behind."""
    from rasterio.vrt import WarpedVRT
    with rasterio.open('tests/data/goes.tif') as src:
        with WarpedVRT(src, dst_crs="EPSG:3857") as vrt:
            pass
        assert "Ignoring error" in caplog.text
        _ = src.colorinterp

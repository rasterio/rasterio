import boto3
from packaging.version import parse
import pytest

import rasterio
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window

# Custom markers.
mingdalversion = pytest.mark.skipif(
    parse(rasterio.__gdal_version__) < parse('2.1.0dev'),
    reason="S3 raster access requires GDAL 2.1")

credentials = pytest.mark.skipif(
    not(boto3.Session()._session.get_credentials()),
    reason="S3 raster access requires credentials")


def test_wrap_file(path_rgb_byte_tif):
    """A warp wrapper's dataset has the expected properties"""
    with rasterio.open(path_rgb_byte_tif) as src:
        with WarpedVRT(src, dst_crs='EPSG:3857') as vrt:
            assert vrt.crs == 'EPSG:3857'
            assert tuple(round(x, 1) for x in vrt.bounds) == (
                -8789636.7, 2700460.0, -8524406.4, 2943560.2)
            assert vrt.name.startswith('WarpedVRT(')
            assert vrt.name.endswith('tests/data/RGB.byte.tif')
            assert vrt.indexes == (1, 2, 3)
            assert vrt.nodatavals == (0, 0, 0)
            assert vrt.dtypes == ('uint8', 'uint8', 'uint8')
            assert vrt.read().shape == (3, 736, 803)


def test_extras(path_rgb_byte_tif):
    """The cutline extra has expected effect

    TODO: add a GeoJSON cutline option."""
    with rasterio.open(path_rgb_byte_tif) as src:
        with WarpedVRT(
                src, dst_crs='EPSG:3857',
                cutline='POLYGON ((400 400, 400 401, 401 401, 400 400))') as vrt:
            rgb = vrt.read()
            assert len(rgb[rgb > 0]) == 3


@mingdalversion
@credentials
@pytest.mark.network
def test_wrap_s3():
    """A warp wrapper's dataset has the expected properties"""
    L8TIF = "s3://landsat-pds/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF"
    with rasterio.open(L8TIF) as src:
        with WarpedVRT(src, dst_crs='EPSG:3857') as vrt:
            assert vrt.crs == 'EPSG:3857'
            assert tuple(round(x, 1) for x in vrt.bounds) == (
                9556764.6, 2345109.3, 9804595.9, 2598509.1)
            assert vrt.name == 'WarpedVRT(s3://landsat-pds/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF)'
            assert vrt.indexes == (1,)
            assert vrt.nodatavals == (None,)
            assert vrt.dtypes == ('uint16',)
            assert vrt.shape == (7827, 7655)

"""``pytest`` fixtures."""


import functools
import operator
import os
import shutil
import sys
import zipfile

import affine
from click.testing import CliRunner
import py
import pytest
import numpy as np

import rasterio
from rasterio.crs import CRS
from rasterio.enums import ColorInterp
from rasterio.env import GDALVersion


DEFAULT_SHAPE = (10, 10)


if sys.version_info > (3,):
    reduce = functools.reduce

test_files = [os.path.join(os.path.dirname(__file__), p) for p in [
    'data/RGB.byte.tif', 'data/float.tif', 'data/float_nan.tif',
    'data/shade.tif', 'data/RGBA.byte.tif']]


def pytest_cmdline_main(config):
    # Bail if the test raster data is not present. Test data is not
    # distributed with sdists since 0.12.
    if reduce(operator.and_, map(os.path.exists, test_files)):
        print("Test data present.")
    else:
        print("Test data not present. See download directions in "
              "tests/data/README.rst")
        sys.exit(1)


@pytest.fixture(scope='function')
def runner():
    return CliRunner()


@pytest.fixture(scope='function')
def data():
    """A temporary directory containing a copy of the files in data."""
    tmpdir = py.test.ensuretemp('tests/data')
    for filename in test_files:
        shutil.copy(filename, str(tmpdir))
    return tmpdir


@pytest.fixture
def basic_geometry():
    """
    Returns
    -------

    dict: GeoJSON-style geometry object.
        Coordinates are in grid coordinates (Affine.identity()).
    """

    return {
        'type': 'Polygon',
        'coordinates': [[(2, 2), (2, 4.25), (4.25, 4.25), (4.25, 2), (2, 2)]]
    }


@pytest.fixture
def geojson_point():
    """
    Returns
    -------

    dict: GeoJSON-style Point geometry object.
        Coordinates are in grid coordinates (Affine.identity()).
    """

    return {
        'type': 'Point',
        'coordinates': (2, 2)
    }


@pytest.fixture
def geojson_multipoint():
    """
    Returns
    -------

    dict: GeoJSON-style MultiPoint geometry object.
        Coordinates are in grid coordinates (Affine.identity()).
    """

    return {
        'type': 'MultiPoint',
        'coordinates': ((2, 2), (4, 4))
    }


@pytest.fixture
def geojson_line():
    """
    Returns
    -------

    dict: GeoJSON-style LineString geometry object.
        Coordinates are in grid coordinates (Affine.identity()).
    """

    return {
        'type': 'LineString',
        'coordinates': ((2, 2), (4, 4))
    }


@pytest.fixture
def geojson_multiline():
    """
    Returns
    -------

    dict: GeoJSON-style MultiLineString geometry object.
        Coordinates are in grid coordinates (Affine.identity()).
    """

    return {
        'type': 'MultiLineString',
        'coordinates': (((2, 2), (4, 4)), ((0, 0), (4, 0)))
    }


@pytest.fixture
def geojson_polygon(basic_geometry):
    """
    Returns
    -------

    dict: GeoJSON-style Polygon geometry object.
        Coordinates are in grid coordinates (Affine.identity()).
    """

    return basic_geometry


@pytest.fixture
def geojson_multipolygon():
    """
    Returns
    -------

    dict: GeoJSON-style MultiPolygon geometry object.
        Coordinates are in grid coordinates (Affine.identity()).
    """

    return {
        'type': 'MultiPolygon',
        'coordinates': (
            (((2, 2), (2, 4), (4, 4), (4, 2), (2, 2)), ),
            (((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)), )
        )
    }


@pytest.fixture
def geojson_geomcollection():
    """
    Returns
    -------

    dict: GeoJSON-style GeometryCollection object.
        Coordinates are in grid coordinates (Affine.identity()).
    """

    return {
        'type': 'GeometryCollection',
        'geometries': (
            {
                'type': 'Polygon',
                'coordinates': (((2, 2), (2, 4), (4, 4), (4, 2), (2, 2)), )
            },
            {
                'type': 'Polygon',
                'coordinates': (((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)), )
            }
        )
    }



@pytest.fixture
def basic_feature(basic_geometry):
    """
    Returns
    -------

    dict: GeoJSON object.
        Coordinates are in grid coordinates (Affine.identity()).
    """

    return {
        'geometry': basic_geometry,
        'properties': {
            'val': 15
        },
        'type': 'Feature'
    }


@pytest.fixture
def basic_featurecollection(basic_feature):
    """
    Returns
    -------

    dict: GeoJSON FeatureCollection object.
        Coordinates are in grid coordinates (Affine.identity()).
    """

    return {
        'features': [basic_feature],
        'type': 'FeatureCollection'
    }


@pytest.fixture
def basic_image():
    """
    A basic 10x10 array for testing sieve and shapes functions.
    Contains a square feature 3x3 (size 9).
    Equivalent to results of rasterizing basic_geometry with all_touched=True.

    Returns
    -------

    np ndarray
    """

    image = np.zeros(DEFAULT_SHAPE, dtype=np.uint8)
    image[2:5, 2:5] = 1

    return image


@pytest.fixture
def basic_image_2x2():
    """
    A basic 10x10 array for testing sieve and shapes functions.
    Contains a square feature 2x2 (size 4).
    Equivalent to results of rasterizing basic_geometry with all_touched=False.

    Returns
    -------

    np ndarray
    """

    image = np.zeros(DEFAULT_SHAPE, dtype=np.uint8)
    image[2:4, 2:4] = 1

    return image


@pytest.fixture
def basic_image_2x2x2():
    """
    A basic 10x10 array for testing sieve and shapes functions.
    Contains a square feature 2x2 (size 4).
    Equivalent to results of rasterizing two times the basic_geometry with
    merge_alg='add'.

    Returns
    -------

    np ndarray
    """

    image = np.zeros(DEFAULT_SHAPE, dtype=np.uint8)
    image[2:4, 2:4] = 2

    return image


@pytest.fixture
def pixelated_image(basic_image):
    """
    A basic 10x10 array for testing sieve functions.  Contains a square feature
    3x3 (size 9), with 2 isolated pixels.

    Returns
    -------

    np ndarray
    """

    image = basic_image.copy()
    image[0, 0] = 1
    image[8, 8] = 1

    return image


@pytest.fixture
def diagonal_image():
    """
    A 10x10 array for testing sieve functions, with only one diagonal filled.

    Returns
    -------

    np ndarray
    """

    image = np.zeros(DEFAULT_SHAPE, dtype=np.uint8)
    np.fill_diagonal(image, 1)
    return image


@pytest.fixture()
def basic_image_file(tmpdir, basic_image):
    """
    A basic raster file with a 10x10 array for testing sieve functions.
    Contains data from pixelated_image.

    Returns
    -------

    string
        Filename of test raster file
    """

    from affine import Affine
    import rasterio

    image = basic_image

    outfilename = str(tmpdir.join('basic_image.tif'))
    kwargs = {
        "crs": CRS({'init': 'epsg:4326'}),
        "transform": Affine.identity(),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": image.shape[1],
        "height": image.shape[0],
        "nodata": None
    }
    with rasterio.open(outfilename, 'w', **kwargs) as out:
        out.write(image, indexes=1)

    return outfilename


@pytest.fixture()
def pixelated_image_file(tmpdir, pixelated_image):
    """
    A basic raster file with a 10x10 array for testing sieve functions.
    Contains data from pixelated_image.

    Returns
    -------

    string
        Filename of test raster file
    """

    from affine import Affine
    import rasterio

    image = pixelated_image

    outfilename = str(tmpdir.join('pixelated_image.tif'))
    kwargs = {
        "crs": CRS({'init': 'epsg:4326'}),
        "transform": Affine.identity(),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": image.shape[1],
        "height": image.shape[0],
        "nodata": 255
    }
    with rasterio.open(outfilename, 'w', **kwargs) as out:
        out.write(image, indexes=1)

    return outfilename


@pytest.fixture(scope='function')
def gdalenv(request):
    import rasterio.env

    def fin():
        if rasterio.env.local._env:
            rasterio.env.delenv()
            rasterio.env.local._env = None
    request.addfinalizer(fin)


@pytest.fixture(scope='session')
def data_dir():
    """Absolute file path to the directory containing test datasets."""
    return os.path.abspath(os.path.join('tests', 'data'))


@pytest.fixture(scope='session')
def path_rgb_byte_tif(data_dir):
    return os.path.join(data_dir, 'RGB.byte.tif')


@pytest.fixture(scope='session')
def path_rgba_byte_tif(data_dir):
    return os.path.join(data_dir, 'RGBA.byte.tif')


@pytest.fixture(scope='function')
def _path_multiband_no_colorinterp(tmpdir):

    """Produces a function for generating an image with ``count`` bands
    and undefined color interpretation.  May trigger a PAM file depending on
    the GDAL version.

    Returns
    -------
    function
    """

    def _create_path_multiband_no_colorinterp(count):
        # For GDAL 2.2.2 the first band can be 'undefined', but on older
        # versions it must be 'gray'.
        undefined_ci = [ColorInterp.gray]
        if count > 1:
            undefined_ci += [ColorInterp.undefined] * (count - 1)
        dst_path = str(tmpdir.join('4band-byte-no-ci.tif'))
        profile = {
            'height': 10,
            'width': 10,
            'count': count,
            'dtype': rasterio.ubyte,
            'transform': affine.Affine(1, 0.0, 0,
                                       0.0, -1, 1),
            'driver': 'GTiff',
            'photometric': 'minisblack'
        }

        undefined_ci = tuple(undefined_ci)
        with rasterio.open(dst_path, 'w', **profile) as src:
            src.colorinterp = undefined_ci

        # Ensure override occurred.  Setting color interpretation on an
        # existing file is surrounded by traps and forceful GDAL assumptions,
        # especially on older versions.
        with rasterio.open(dst_path) as src:
            if src.colorinterp != undefined_ci:
                raise ValueError(
                    "Didn't properly set color interpretation.  GDAL can "
                    "forcefully make assumptions.")

        return dst_path

    return _create_path_multiband_no_colorinterp


@pytest.fixture(scope='function')
def path_3band_no_colorinterp(_path_multiband_no_colorinterp):
    """A 3 band image with undefined color interpretation."""
    return _path_multiband_no_colorinterp(3)


@pytest.fixture(scope='function')
def path_4band_no_colorinterp(_path_multiband_no_colorinterp):
    """A 4 band image with undefined color interpretation."""
    return _path_multiband_no_colorinterp(4)


@pytest.fixture(scope='session')
def path_float_tif(data_dir):
    return os.path.join(data_dir, 'float.tif')


@pytest.fixture(scope='session')
def path_zip_file():
    """Creates ``coutwildrnp.zip`` if it does not exist and returns
    the absolute file path."""
    path = '{}/white-gemini-iv.zip'.format(data_dir())
    if not os.path.exists(path):
        with zipfile.ZipFile(path, 'w') as zip:
            for filename in ['white-gemini-iv.vrt',
                             '389225main_sw_1965_1024.jpg']:
                zip.write(os.path.join(data_dir(), filename), filename)
    return path


# Define helpers to skip tests based on GDAL version
gdal_version = GDALVersion.runtime()

requires_only_gdal1 = pytest.mark.skipif(
    gdal_version.major != 1,
    reason="Only relevant for GDAL 1.x")

requires_gdal110 = pytest.mark.skipif(
    not gdal_version.at_least('1.10'),
    reason="Requires GDAL 1.10.x")

requires_gdal2 = pytest.mark.skipif(
    not gdal_version.major >= 2,
    reason="Requires GDAL 2.x")

requires_gdal21 = pytest.mark.skipif(
    not gdal_version.at_least('2.1'),
    reason="Requires GDAL 2.1.x")

requires_gdal22 = pytest.mark.skipif(
    not gdal_version.at_least('2.2'),
    reason="Requires GDAL 2.2.x")
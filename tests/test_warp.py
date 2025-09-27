"""rasterio.warp module tests"""

import logging
import os
import re
import sys

from affine import Affine
import numpy as np
from numpy.testing import assert_almost_equal
import pytest

import rasterio
from rasterio._err import CPLE_AppDefinedError
from rasterio.control import GroundControlPoint
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.errors import (
    CRSError,
    GDALVersionError,
    TransformError,
    RPCError,
    WarpOperationError,
)
from rasterio.warp import (
    reproject,
    transform_geom,
    transform,
    transform_bounds,
    calculate_default_transform,
    aligned_target,
    SUPPORTED_RESAMPLING,
)
from rasterio import windows

from . import rangehttpserver
from .conftest import gdal_version

log = logging.getLogger(__name__)

# Make a gdal version tuple.
version_name = rasterio.gdal_version()
version_name = re.split(r"[a-z]", version_name)[0]
gdal_version_info = tuple(int(x) for x in version_name.split("."))

DST_TRANSFORM = Affine(300.0, 0.0, -8789636.708, 0.0, -300.0, 2943560.235)


def flatten_coords(coordinates):
    """Yield a flat sequence of coordinates to help testing"""
    for elem in coordinates:
        if isinstance(elem, (float, int)):
            yield elem

        else:
            yield from flatten_coords(elem)


if gdal_version.at_least("3.6"):
    # GH2662
    reproj_expected = (
        ({"CHECK_WITH_INVERT_PROJ": False}, 6646),
        ({"CHECK_WITH_INVERT_PROJ": True}, 6646),
    )
else:
    reproj_expected = (
        ({"CHECK_WITH_INVERT_PROJ": False}, 6644),
        ({"CHECK_WITH_INVERT_PROJ": True}, 6644),
    )


class ReprojectParams:
    """Class to assist testing reprojection by encapsulating parameters."""

    def __init__(self, left, bottom, right, top, width, height, src_crs, dst_crs):
        self.width = width
        self.height = height
        src_res = float(right - left) / float(width)
        self.src_transform = Affine(src_res, 0, left, 0, -src_res, top)
        self.src_crs = src_crs
        self.dst_crs = dst_crs

        dt, dw, dh = calculate_default_transform(
            src_crs, dst_crs, width, height, left, bottom, right, top
        )
        self.dst_transform = dt
        self.dst_width = dw
        self.dst_height = dh


def default_reproject_params():
    return ReprojectParams(
        left=-120,
        bottom=30,
        right=-80,
        top=70,
        width=80,
        height=80,
        src_crs=CRS.from_epsg(4326),
        dst_crs=CRS.from_epsg(2163),
    )


def uninvertable_reproject_params():
    return ReprojectParams(
        left=-120,
        bottom=30,
        right=-80,
        top=70,
        width=80,
        height=80,
        src_crs=CRS.from_epsg(4326),
        dst_crs=CRS.from_epsg(26836),
    )


WGS84_crs = CRS.from_epsg(4326)


class RangeRequestErrorHandler(rangehttpserver.RangeRequestHandler):
    """Return 500 for a range of bytes to simulate a malfunctioning server.

    The byte range is specific to rasterio's RGB.byte.tif file.

    """

    def send_head(self):
        if "Range" not in self.headers:
            self.range = None
            return super().send_head()
        try:
            self.range = rangehttpserver.parse_byte_range(self.headers["Range"])
        except ValueError as e:
            self.send_error(400, "Invalid byte range")
            return None
        first, last = self.range

        # Our "poison byte" is at position 1609000.
        if first <= 1609000 <= last:
            self.send_error(500, "Boom!")
            return None

        # Mirroring SimpleHTTPServer.py here
        path = self.translate_path(self.path)
        f = None
        ctype = self.guess_type(path)
        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return None

        fs = os.fstat(f.fileno())
        file_len = fs[6]
        if first >= file_len:
            self.send_error(416, "Requested Range Not Satisfiable")
            return None

        self.send_response(206)
        self.send_header("Content-type", ctype)
        self.send_header("Accept-Ranges", "bytes")

        if last is None or last >= file_len:
            last = file_len - 1
        response_length = last - first + 1

        self.send_header(
            "Content-Range", "bytes {}-{}/{}".format(first, last, file_len)
        )
        self.send_header("Content-Length", str(response_length))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f


@pytest.fixture(scope="session")
def rpcs():
    with rasterio.open("tests/data/RGB.byte.rpc.vrt") as src:
        return src.rpcs


def test_transform_src_crs_none():
    with pytest.raises(CRSError):
        transform(None, WGS84_crs, [1], [1])


def test_transform_dst_crs_none():
    with pytest.raises(CRSError):
        transform(WGS84_crs, None, [1], [1])


def test_transform_bounds_src_crs_none():
    with pytest.raises(CRSError):
        transform_bounds(None, WGS84_crs, 0, 0, 0, 0)


def test_transform_bounds_dst_crs_none():
    with pytest.raises(CRSError):
        transform_bounds(WGS84_crs, None, 0, 0, 0, 0)


def test_transform_geom_src_crs_none():
    with pytest.raises(CRSError):
        transform_geom(None, WGS84_crs, None)


def test_transform_geom_dst_crs_none():
    with pytest.raises(CRSError):
        transform_geom(WGS84_crs, None, None)


def test_reproject_src_crs_none():
    with pytest.raises(CRSError):
        reproject(
            np.ones((2, 2)),
            np.zeros((2, 2)),
            src_transform=Affine.identity(),
            dst_transform=Affine.identity(),
            dst_crs=WGS84_crs,
        )


def test_reproject_dst_crs_none():
    with pytest.raises(CRSError):
        reproject(
            np.ones((2, 2)),
            np.zeros((2, 2)),
            src_transform=Affine.identity(),
            dst_transform=Affine.identity(),
            src_crs=WGS84_crs,
        )


def test_transform():
    """2D and 3D."""
    WGS84_crs = CRS.from_epsg(4326)
    WGS84_points = ([12.492269], [41.890169], [48.0])
    ECEF_crs = CRS.from_epsg(4978)
    ECEF_points = ([4642610.0], [1028584.0], [4236562.0])
    ECEF_result = transform(WGS84_crs, ECEF_crs, *WGS84_points)
    assert np.allclose(np.array(ECEF_result), np.array(ECEF_points))

    UTM33_crs = CRS.from_epsg(32633)
    UTM33_points = ([291952], [4640623])
    UTM33_result = transform(WGS84_crs, UTM33_crs, *WGS84_points[:2])
    assert np.allclose(np.array(UTM33_result), np.array(UTM33_points))


def test_transform_bounds():
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        l, b, r, t = src.bounds
        assert np.allclose(
            transform_bounds(src.crs, CRS.from_epsg(4326), l, b, r, t),
            (
                -78.95864996545055,
                23.564991210854686,
                -76.57492370013823,
                25.550873767433984,
            ),
        )


def test_transform_bounds__esri_wkt():
    left, bottom, right, top = (
        -78.95864996545055,
        23.564991210854686,
        -76.57492370013823,
        25.550873767433984,
    )
    dst_projection_string = (
        'PROJCS["USA_Contiguous_Albers_Equal_Area_Conic_USGS_version",'
        'GEOGCS["GCS_North_American_1983",DATUM["D_North_American_1983",'
        'SPHEROID["GRS_1980",6378137.0,298.257222101]],'
        'PRIMEM["Greenwich",0.0],'
        'UNIT["Degree",0.0174532925199433]],'
        'PROJECTION["Albers"],'
        'PARAMETER["false_easting",0.0],'
        'PARAMETER["false_northing",0.0],'
        'PARAMETER["central_meridian",-96.0],'
        'PARAMETER["standard_parallel_1",29.5],'
        'PARAMETER["standard_parallel_2",45.5],'
        'PARAMETER["latitude_of_origin",23.0],'
        'UNIT["Meter",1.0],'
        'VERTCS["NAVD_1988",'
        'VDATUM["North_American_Vertical_Datum_1988"],'
        'PARAMETER["Vertical_Shift",0.0],'
        'PARAMETER["Direction",1.0],UNIT["Centimeter",0.01]]]'
    )
    assert np.allclose(
        transform_bounds(
            CRS.from_epsg(4326), dst_projection_string, left, bottom, right, top
        ),
        (1721263.7931814701, 219684.49332178483, 2002926.56696663, 479360.16562217404),
    )


@pytest.mark.xfail(reason="Projection extents have changed with PROJ 9")
@pytest.mark.parametrize(
    "density,expected",
    [
        (0, (-1684649.41338, -350356.81377, 1684649.41338, 2234551.18559)),
        (100, (-1684649.41338, -555777.79210, 1684649.41338, 2234551.18559)),
    ],
)
def test_transform_bounds_densify(density, expected):
    # This transform is non-linear along the edges, so densification produces
    # a different result than otherwise
    src_crs = CRS.from_epsg(4326)
    dst_crs = CRS.from_proj4(
        "+proj=laea +lat_0=45 +lon_0=-100 +x_0=0 +y_0=0 "
        "+a=6370997 +b=6370997 +units=m +no_defs"
    )
    assert np.allclose(
        expected,
        transform_bounds(src_crs, dst_crs, -120, 40, -80, 64, densify_pts=density),
    )


def test_transform_bounds_no_change():
    """Make sure that going from and to the same crs causes no change."""
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        l, b, r, t = src.bounds
        assert np.allclose(transform_bounds(src.crs, src.crs, l, b, r, t), src.bounds)


def test_transform_bounds_densify_out_of_bounds():
    with pytest.raises(CPLE_AppDefinedError):
        transform_bounds(
            CRS.from_epsg(4326),
            CRS.from_epsg(32610),
            -120,
            40,
            -80,
            64,
            densify_pts=-10,
        )


def test_calculate_default_transform():
    target_transform = Affine(
        0.0028535715391804096,
        0.0,
        -78.95864996545055,
        0.0,
        -0.0028535715391804096,
        25.550873767433984,
    )

    with rasterio.open("tests/data/RGB.byte.tif") as src:
        wgs84_crs = CRS.from_epsg(4326)
        dst_transform, width, height = calculate_default_transform(
            src.crs, wgs84_crs, src.width, src.height, *src.bounds
        )

        assert dst_transform.almost_equals(target_transform)
        assert width == 835
        assert height == 696


def test_calculate_default_transform_geoloc_array():
    target_transform = Affine(
        0.0028535715391804096,
        0.0,
        -78.95864996545055,
        0.0,
        -0.0028535715391804096,
        25.550873767433984,
    )

    with rasterio.open("tests/data/RGB.byte.tif") as src:
        xs, ys = src.transform * np.meshgrid(
            np.arange(0, src.width, 10), np.arange(0, src.height, 10)
        )
        dst_transform, width, height = calculate_default_transform(
            src.crs,
            CRS.from_epsg(4326),
            src.width,
            src.height,
            src_geoloc_array=(xs, ys),
        )

        assert dst_transform.almost_equals(target_transform, precision=1e-3)
        assert width == 838
        assert height == 692


def test_calculate_default_transform_rpcs(rpcs):
    target_transform = Affine(
        7.516528579807828e-05,
        0.0,
        -123.48824818566493,
        0.0,
        -7.516528579807828e-05,
        49.52797830474044,
    )

    dst_transform, width, height = calculate_default_transform(
        CRS.from_epsg(32618),
        CRS.from_epsg(4326),
        791,
        718,
        rpcs=rpcs,
    )

    assert dst_transform.almost_equals(target_transform, precision=1e-4)
    assert height == 553
    assert width == 1144


def test_calculate_default_transform_single_resolution():
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        target_resolution = 0.1
        target_transform = Affine(
            target_resolution,
            0.0,
            -78.95864996545055,
            0.0,
            -target_resolution,
            25.550873767433984,
        )
        dst_transform, width, height = calculate_default_transform(
            src.crs,
            CRS.from_epsg(4326),
            src.width,
            src.height,
            *src.bounds,
            resolution=target_resolution,
        )

        assert dst_transform.almost_equals(target_transform)
        assert width == 24
        assert height == 20


def test_calculate_default_transform_multiple_resolutions():
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        target_resolution = (0.2, 0.1)
        target_transform = Affine(
            target_resolution[0],
            0.0,
            -78.95864996545055,
            0.0,
            -target_resolution[1],
            25.550873767433984,
        )

        dst_transform, width, height = calculate_default_transform(
            src.crs,
            CRS.from_epsg(4326),
            src.width,
            src.height,
            *src.bounds,
            resolution=target_resolution,
        )

        assert dst_transform.almost_equals(target_transform)
        assert width == 12
        assert height == 20


def test_calculate_default_transform_dimensions():
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        dst_width, dst_height = (113, 103)
        target_transform = Affine(
            0.02108612597535966,
            0.0,
            -78.95864996545055,
            0.0,
            -0.0192823863230055,
            25.550873767433984,
        )

        dst_transform, width, height = calculate_default_transform(
            src.crs,
            CRS.from_epsg(4326),
            src.width,
            src.height,
            *src.bounds,
            dst_width=dst_width,
            dst_height=dst_height,
        )

        assert dst_transform.almost_equals(target_transform)
        assert width == dst_width
        assert height == dst_height


def test_reproject_ndarray():
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        source = src.read(1)

    dst_crs = dict(
        proj="merc",
        a=6378137,
        b=6378137,
        lat_ts=0.0,
        lon_0=0.0,
        x_0=0.0,
        y_0=0,
        k=1.0,
        units="m",
        nadgrids="@null",
        wktext=True,
        no_defs=True,
    )
    out = np.empty(src.shape, dtype=np.uint8)
    reproject(
        source,
        out,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=DST_TRANSFORM,
        dst_crs=dst_crs,
        resampling=Resampling.nearest,
    )
    assert (out > 0).sum() == 438113


def test_reproject_ndarray_slice():
    """Test for issue #2511, destination with strides"""

    with rasterio.open("tests/data/RGB.byte.tif") as src:
        source = src.read(1)

    dst_crs = dict(
        proj="merc",
        a=6378137,
        b=6378137,
        lat_ts=0.0,
        lon_0=0.0,
        x_0=0.0,
        y_0=0,
        k=1.0,
        units="m",
        nadgrids="@null",
        wktext=True,
        no_defs=True,
    )

    out = np.zeros((src.count, src.height, src.width + 2), dtype=np.uint8)[..., 1:-1]
    assert out.__array_interface__["strides"] is not None
    reproject(
        source,
        out,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=DST_TRANSFORM,
        dst_crs=dst_crs,
        resampling=Resampling.nearest,
    )
    assert (out > 0).sum() == 438113


def test_reproject_view():
    """Source views are reprojected properly"""
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        source = src.read(1)

    window = windows.Window(100, 100, 500, 500)
    # window = windows.get_data_window(source)
    reduced_array = source[window.toslices()]
    reduced_transform = windows.transform(window, src.transform)

    # Assert that we're working with a view.
    assert reduced_array.base is source

    dst_crs = dict(
        proj="merc",
        a=6378137,
        b=6378137,
        lat_ts=0.0,
        lon_0=0.0,
        x_0=0.0,
        y_0=0,
        k=1.0,
        units="m",
        nadgrids="@null",
        wktext=True,
        no_defs=True,
    )

    out = np.empty(src.shape, dtype=np.uint8)

    reproject(
        reduced_array,
        out,
        src_transform=reduced_transform,
        src_crs=src.crs,
        dst_transform=DST_TRANSFORM,
        dst_crs=dst_crs,
        resampling=Resampling.nearest,
    )

    expected_sum = 299199
    if gdal_version.at_least("3.6"):
        # GH2662
        expected_sum = 299231
    assert (out > 0).sum() == expected_sum


def test_reproject_epsg():
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        source = src.read(1)

    dst_crs = {"init": "epsg:3857"}
    out = np.empty(src.shape, dtype=np.uint8)
    reproject(
        source,
        out,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=DST_TRANSFORM,
        dst_crs=dst_crs,
        resampling=Resampling.nearest,
    )
    assert (out > 0).sum() == 438113


def test_reproject_epsg__simple_array():
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        source = src.read(1)

    dst_crs = {"init": "EPSG:3857"}
    out, dst_transform = reproject(
        source,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_crs=dst_crs,
        resampling=Resampling.nearest,
    )
    assert (out > 0).sum() == 383077
    assert_almost_equal(
        tuple(dst_transform),
        tuple(
            Affine(
                330.2992903555146,
                0.0,
                -8789636.707871985,
                0.0,
                -330.2992903555146,
                2943560.2346221623,
            )
        ),
        decimal=5,
    )


def test_reproject_epsg__simple_array_resolution():
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        source = src.read(1)

    dst_crs = {"init": "EPSG:3857"}
    out, dst_transform = reproject(
        source,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_crs=dst_crs,
        dst_resolution=(300, 300),
        resampling=Resampling.nearest,
    )
    assert (out > 0).sum() == 464503
    assert_almost_equal(
        tuple(dst_transform),
        tuple(Affine(300, 0.0, -8789636.707871985, 0.0, -300, 2943560.2346221623)),
        decimal=5,
    )


def test_reproject_epsg__simple_array_dst():
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        source = src.read(1)

    dst_crs = {"init": "EPSG:3857"}
    dst_out = np.empty(src.shape, dtype=np.uint8)

    out, dst_transform = reproject(
        source,
        dst_out,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_crs=dst_crs,
        resampling=Resampling.nearest,
    )
    assert (out > 0).sum() == 368123
    assert_almost_equal(
        tuple(dst_transform),
        tuple(
            Affine(
                335.3101519032594,
                0.0,
                -8789636.707871985,
                0.0,
                -338.579773957742,
                2943560.2346221623,
            )
        ),
        decimal=5,
    )


def test_reproject_epsg__simple():
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        dst_crs = {"init": "EPSG:3857"}
        out, dst_transform = reproject(
            rasterio.band(src, 1),
            dst_crs=dst_crs,
            resampling=Resampling.nearest,
        )
    assert (out > 0).sum() == 383077
    assert_almost_equal(
        tuple(dst_transform),
        tuple(
            Affine(
                330.2992903555146,
                0.0,
                -8789636.707871985,
                0.0,
                -330.2992903555146,
                2943560.2346221623,
            )
        ),
        decimal=5,
    )


def test_reproject_epsg__simple_resolution():
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        dst_crs = {"init": "EPSG:3857"}
        out, dst_transform = reproject(
            rasterio.band(src, 1),
            dst_crs=dst_crs,
            dst_resolution=(300, 300),
            resampling=Resampling.nearest,
        )
    assert (out > 0).sum() == 464503
    assert_almost_equal(
        tuple(dst_transform),
        tuple(Affine(300.0, 0.0, -8789636.707871985, 0.0, -300.0, 2943560.2346221623)),
        decimal=5,
    )


def test_reproject_no_destination_with_transform():
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        source = src.read(1)

    dst_crs = {"init": "EPSG:3857"}
    with pytest.raises(ValueError):
        reproject(
            source,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_crs=dst_crs,
            dst_transform=DST_TRANSFORM,
            resampling=Resampling.nearest,
        )


def test_reproject_out_of_bounds():
    """Using EPSG code is not appropriate for the transform.

    Should return blank image.
    """
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        source = src.read(1)

    dst_crs = {"init": "epsg:32619"}
    out = np.zeros(src.shape, dtype=np.uint8)
    reproject(
        source,
        out,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=DST_TRANSFORM,
        dst_crs=dst_crs,
        resampling=Resampling.nearest,
    )
    assert not out.any()


@pytest.mark.parametrize("options, expected", reproj_expected)
def test_reproject_nodata(options, expected):
    # Older combinations of GDAL and PROJ might have got this transformation wrong.
    # Results look better with GDAL 3.
    nodata = 215

    with rasterio.Env(**options):
        params = uninvertable_reproject_params()
        source = np.ones((params.width, params.height), dtype=np.uint8)
        out = np.zeros((params.dst_width, params.dst_height), dtype=source.dtype)
        out.fill(120)  # Fill with arbitrary value

        reproject(
            source,
            out,
            src_transform=params.src_transform,
            src_crs=params.src_crs,
            src_nodata=nodata,
            dst_transform=params.dst_transform,
            dst_crs=params.dst_crs,
            dst_nodata=nodata,
        )

        assert (out == 1).sum() == expected
        assert (out == nodata).sum() == (
            params.dst_width * params.dst_height - expected
        )


@pytest.mark.parametrize("options, expected", reproj_expected)
def test_reproject_nodata_nan(options, expected):
    with rasterio.Env(**options):
        params = uninvertable_reproject_params()
        source = np.ones((params.width, params.height), dtype=np.float32)
        out = np.zeros((params.dst_width, params.dst_height), dtype=source.dtype)
        out.fill(120)  # Fill with arbitrary value

        reproject(
            source,
            out,
            src_transform=params.src_transform,
            src_crs=params.src_crs,
            src_nodata=np.nan,
            dst_transform=params.dst_transform,
            dst_crs=params.dst_crs,
            dst_nodata=np.nan,
        )

        assert (out == 1).sum() == expected
        assert np.isnan(out).sum() == (params.dst_width * params.dst_height - expected)


@pytest.mark.parametrize("options, expected", reproj_expected)
def test_reproject_dst_nodata_default(options, expected):
    """If nodata is not provided, destination will be filled with 0."""

    with rasterio.Env(**options):
        params = uninvertable_reproject_params()
        source = np.ones((params.width, params.height), dtype=np.uint8)
        out = np.zeros((params.dst_width, params.dst_height), dtype=source.dtype)
        out.fill(120)  # Fill with arbitrary value

        reproject(
            source,
            out,
            src_transform=params.src_transform,
            src_crs=params.src_crs,
            dst_transform=params.dst_transform,
            dst_crs=params.dst_crs,
        )

        assert (out == 1).sum() == expected
        assert (out == 0).sum() == (params.dst_width * params.dst_height - expected)


def test_reproject_invalid_dst_nodata():
    """dst_nodata must be in value range of data type."""
    params = default_reproject_params()

    source = np.ones((params.width, params.height), dtype=np.uint8)
    out = source.copy()

    with pytest.raises(ValueError):
        reproject(
            source,
            out,
            src_transform=params.src_transform,
            src_crs=params.src_crs,
            src_nodata=0,
            dst_transform=params.dst_transform,
            dst_crs=params.dst_crs,
            dst_nodata=999999999,
        )


def test_reproject_invalid_src_nodata():
    """src_nodata must be in range for data type."""
    params = default_reproject_params()

    source = np.ones((params.width, params.height), dtype=np.uint8)
    out = source.copy()

    with pytest.raises(ValueError):
        reproject(
            source,
            out,
            src_transform=params.src_transform,
            src_crs=params.src_crs,
            src_nodata=999999999,
            dst_transform=params.dst_transform,
            dst_crs=params.dst_crs,
            dst_nodata=215,
        )


def test_reproject_init_nodata_tofile(tmpdir):
    """Test that nodata is being initialized."""
    params = default_reproject_params()

    tiffname = str(tmpdir.join("foo.tif"))

    source1 = np.zeros((params.width, params.height), dtype=np.uint8)
    source2 = source1.copy()

    # fill both sources w/ arbitrary values
    rows, cols = source1.shape
    source1[: rows // 2, : cols // 2] = 200
    source2[rows // 2 :, cols // 2 :] = 100

    kwargs = {
        "count": 1,
        "width": params.width,
        "height": params.height,
        "dtype": np.uint8,
        "driver": "GTiff",
        "crs": params.dst_crs,
        "transform": params.dst_transform,
    }

    with rasterio.open(tiffname, "w", **kwargs) as dst:
        reproject(
            source1,
            rasterio.band(dst, 1),
            src_transform=params.src_transform,
            src_crs=params.src_crs,
            src_nodata=0.0,
            dst_transform=params.dst_transform,
            dst_crs=params.dst_crs,
            dst_nodata=0.0,
        )

        # 200s should be overwritten by 100s
        reproject(
            source2,
            rasterio.band(dst, 1),
            src_transform=params.src_transform,
            src_crs=params.src_crs,
            src_nodata=0.0,
            dst_transform=params.dst_transform,
            dst_crs=params.dst_crs,
            dst_nodata=0.0,
        )

    with rasterio.open(tiffname) as src:
        assert src.read().max() == 100


def test_reproject_no_init_nodata_tofile(tmpdir):
    """Test that nodata is not being initialized."""
    params = default_reproject_params()

    tiffname = str(tmpdir.join("foo.tif"))

    source1 = np.zeros((params.width, params.height), dtype=np.uint8)
    source2 = source1.copy()

    # fill both sources w/ arbitrary values
    rows, cols = source1.shape
    source1[: rows // 2, : cols // 2] = 200
    source2[rows // 2 :, cols // 2 :] = 100

    kwargs = {
        "count": 1,
        "width": params.width,
        "height": params.height,
        "dtype": np.uint8,
        "driver": "GTiff",
        "crs": params.dst_crs,
        "transform": params.dst_transform,
    }

    with rasterio.open(tiffname, "w", **kwargs) as dst:
        reproject(
            source1,
            rasterio.band(dst, 1),
            src_transform=params.src_transform,
            src_crs=params.src_crs,
            src_nodata=0.0,
            dst_transform=params.dst_transform,
            dst_crs=params.dst_crs,
            dst_nodata=0.0,
        )

        reproject(
            source2,
            rasterio.band(dst, 1),
            src_transform=params.src_transform,
            src_crs=params.src_crs,
            src_nodata=0.0,
            dst_transform=params.dst_transform,
            dst_crs=params.dst_crs,
            dst_nodata=0.0,
            init_dest_nodata=False,
        )

    # 200s should remain along with 100s
    with rasterio.open(tiffname) as src:
        data = src.read()

    assert data.max() == 200


def test_reproject_no_init_nodata_toarray():
    """Test that nodata is being initialized."""
    params = default_reproject_params()

    source1 = np.zeros((params.width, params.height))
    source2 = source1.copy()
    out = source1.copy()

    # fill both sources w/ arbitrary values
    rows, cols = source1.shape
    source1[: rows // 2, : cols // 2] = 200
    source2[rows // 2 :, cols // 2 :] = 100

    reproject(
        source1,
        out,
        src_transform=params.src_transform,
        src_crs=params.src_crs,
        src_nodata=0.0,
        dst_transform=params.dst_transform,
        dst_crs=params.dst_crs,
        dst_nodata=0.0,
    )

    assert out.max() == 200
    assert out.min() == 0

    reproject(
        source2,
        out,
        src_transform=params.src_transform,
        src_crs=params.src_crs,
        src_nodata=0.0,
        dst_transform=params.dst_transform,
        dst_crs=params.dst_crs,
        dst_nodata=0.0,
        init_dest_nodata=False,
    )

    # 200s should NOT be overwritten by 100s
    assert out.max() == 200
    assert out.min() == 0


def test_reproject_multi():
    """Ndarry to ndarray."""
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        source = src.read()
    dst_crs = dict(
        proj="merc",
        a=6378137,
        b=6378137,
        lat_ts=0.0,
        lon_0=0.0,
        x_0=0.0,
        y_0=0,
        k=1.0,
        units="m",
        nadgrids="@null",
        wktext=True,
        no_defs=True,
    )
    destin = np.empty(source.shape, dtype=np.uint8)
    reproject(
        source,
        destin,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=DST_TRANSFORM,
        dst_crs=dst_crs,
        resampling=Resampling.nearest,
    )
    assert destin.any()


def test_warp_from_file():
    """File to ndarray."""
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        dst_crs = dict(
            proj="merc",
            a=6378137,
            b=6378137,
            lat_ts=0.0,
            lon_0=0.0,
            x_0=0.0,
            y_0=0,
            k=1.0,
            units="m",
            nadgrids="@null",
            wktext=True,
            no_defs=True,
        )
        destin = np.empty(src.shape, dtype=np.uint8)
        reproject(
            rasterio.band(src, 1), destin, dst_transform=DST_TRANSFORM, dst_crs=dst_crs
        )
    assert destin.any()


def test_warp_from_to_file(tmpdir):
    """File to file."""
    tiffname = str(tmpdir.join("foo.tif"))
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        dst_crs = dict(
            proj="merc",
            a=6378137,
            b=6378137,
            lat_ts=0.0,
            lon_0=0.0,
            x_0=0.0,
            y_0=0,
            k=1.0,
            units="m",
            nadgrids="@null",
            wktext=True,
            no_defs=True,
        )
        kwargs = src.meta.copy()
        kwargs.update(transform=DST_TRANSFORM, crs=dst_crs)
        with rasterio.open(tiffname, "w", **kwargs) as dst:
            for i in (1, 2, 3):
                reproject(rasterio.band(src, i), rasterio.band(dst, i))


def test_warp_from_to_file_multi(tmpdir):
    """File to file."""
    tiffname = str(tmpdir.join("foo.tif"))
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        dst_crs = dict(
            proj="merc",
            a=6378137,
            b=6378137,
            lat_ts=0.0,
            lon_0=0.0,
            x_0=0.0,
            y_0=0,
            k=1.0,
            units="m",
            nadgrids="@null",
            wktext=True,
            no_defs=True,
        )
        kwargs = src.meta.copy()
        kwargs.update(transform=DST_TRANSFORM, crs=dst_crs)
        with rasterio.open(tiffname, "w", **kwargs) as dst:
            for i in (1, 2, 3):
                reproject(rasterio.band(src, i), rasterio.band(dst, i), num_threads=2)


@pytest.fixture(scope="function")
def polygon_3373():
    """An EPSG:3373 polygon."""
    return {
        "type": "Polygon",
        "coordinates": (
            (
                (798842.3090855901, 6569056.500655151),
                (756688.2826828464, 6412397.888771972),
                (755571.0617232556, 6408461.009397383),
                (677605.2284582685, 6425600.39266733),
                (677605.2284582683, 6425600.392667332),
                (670873.3791649605, 6427248.603432341),
                (664882.1106069803, 6407585.48425362),
                (663675.8662823177, 6403676.990080649),
                (485120.71963574126, 6449787.167760638),
                (485065.55660851026, 6449802.826920689),
                (485957.03982722526, 6452708.625101285),
                (487541.24541826674, 6457883.292107048),
                (531008.5797472061, 6605816.560367976),
                (530943.7197027118, 6605834.9333479265),
                (531888.5010308184, 6608940.750411527),
                (533299.5981959199, 6613962.642851984),
                (533403.6388841148, 6613933.172096095),
                (576345.6064638699, 6761983.708069147),
                (577649.6721159086, 6766698.137844516),
                (578600.3589008929, 6770143.99782289),
                (578679.4732294685, 6770121.638265098),
                (655836.640492081, 6749376.357102599),
                (659913.0791150068, 6764770.1314677475),
                (661105.8478791204, 6769515.168134831),
                (661929.4670843681, 6772800.8565198565),
                (661929.4670843673, 6772800.856519875),
                (661975.1582566603, 6772983.354777632),
                (662054.7979028501, 6772962.86384242),
                (841909.6014891531, 6731793.200435557),
                (840726.455490463, 6727039.8672589315),
                (798842.3090855901, 6569056.500655151),
            ),
        ),
    }


def test_transform_geom_polygon_cutting(polygon_3373):
    geom = polygon_3373
    result = transform_geom("EPSG:3373", "EPSG:4326", geom, antimeridian_cutting=True)
    assert result["type"] == "MultiPolygon"
    assert len(result["coordinates"]) == 2


def test_transform_geom_polygon_offset(polygon_3373):
    geom = polygon_3373
    result = transform_geom(
        "EPSG:3373", "EPSG:4326", geom, antimeridian_cutting=True, antimeridian_offset=0
    )
    assert result["type"] == "MultiPolygon"
    assert len(result["coordinates"]) == 2


def test_transform_geom_polygon_precision(polygon_3373):
    geom = polygon_3373
    result = transform_geom(
        "EPSG:3373", "EPSG:4326", geom, precision=1, antimeridian_cutting=True
    )
    assert all(round(x, 1) == x for x in flatten_coords(result["coordinates"]))


def test_transform_geom_linestring_precision(polygon_3373):
    ring = polygon_3373["coordinates"][0]
    geom = {"type": "LineString", "coordinates": ring}
    result = transform_geom(
        "EPSG:3373", "EPSG:4326", geom, precision=1, antimeridian_cutting=True
    )
    assert all(round(x, 1) == x for x in flatten_coords(result["coordinates"]))


def test_transform_geom_linestring_precision_iso(polygon_3373):
    ring = polygon_3373["coordinates"][0]
    geom = {"type": "LineString", "coordinates": ring}
    result = transform_geom("EPSG:3373", "EPSG:3373", geom, precision=1)
    assert int(result["coordinates"][0][0] * 10) == 7988423


def test_transform_geom_linearring_precision(polygon_3373):
    ring = polygon_3373["coordinates"][0]
    geom = {"type": "LinearRing", "coordinates": ring}
    result = transform_geom(
        "EPSG:3373", "EPSG:4326", geom, precision=1, antimeridian_cutting=True
    )
    assert all(round(x, 1) == x for x in flatten_coords(result["coordinates"]))


def test_transform_geom_linestring_precision_z(polygon_3373):
    ring = polygon_3373["coordinates"][0]
    x, y = zip(*ring)
    ring = list(zip(x, y, [0.0 for i in range(len(x))]))
    geom = {"type": "LineString", "coordinates": ring}
    result = transform_geom("EPSG:3373", "EPSG:3373", geom, precision=1)
    assert int(result["coordinates"][0][0] * 10) == 7988423
    assert int(result["coordinates"][0][2] * 10) == 0


def test_transform_geom_multipolygon(polygon_3373):
    geom = {"type": "MultiPolygon", "coordinates": [polygon_3373["coordinates"]]}
    result = transform_geom("EPSG:3373", "EPSG:4326", geom, precision=1)
    assert all(round(x, 1) == x for x in flatten_coords(result["coordinates"]))


def test_transform_geom_array(polygon_3373):
    geom = [polygon_3373 for _ in range(10)]
    result = transform_geom("EPSG:3373", "EPSG:4326", geom, precision=1)
    assert isinstance(result, list)
    assert len(result) == 10


def test_transform_geom__geo_interface(polygon_3373):
    class GeoObj:
        @property
        def __geo_interface__(self):
            return polygon_3373

    result = transform_geom("EPSG:3373", "EPSG:4326", GeoObj(), precision=1)
    assert all(round(x, 1) == x for x in flatten_coords(result["coordinates"]))


def test_transform_geom__geo_interface__array(polygon_3373):
    class GeoObj:
        @property
        def __geo_interface__(self):
            return polygon_3373

    geom = [GeoObj() for _ in range(10)]
    results = transform_geom("EPSG:3373", "EPSG:4326", geom, precision=1)
    assert isinstance(results, list)
    assert len(results) == 10
    for result in results:
        assert all(round(x, 1) == x for x in flatten_coords(result["coordinates"]))


@pytest.mark.parametrize("method", SUPPORTED_RESAMPLING)
def test_reproject_resampling(path_rgb_byte_tif, method):
    # Expected count of nonzero pixels for each resampling method, based
    # on running rasterio with each of the following configurations
    expected = {
        Resampling.nearest: [438113],
        Resampling.bilinear: [439280],
        Resampling.cubic: [437888],
        Resampling.cubic_spline: [440475],
        Resampling.lanczos: [436001],
        Resampling.average: [439172],
        Resampling.mode: [437298, 438002],  # 438002 for GDAL 3.11+.
        Resampling.max: [439464],
        Resampling.min: [436397],
        Resampling.med: [437194],
        Resampling.q1: [436397],
        Resampling.q3: [438948],
        Resampling.sum: [439118, 439142],  # 439142 for GDAL 3.6+
        Resampling.rms: [439385],
    }

    with rasterio.open(path_rgb_byte_tif) as src:
        source = src.read(1)

    out = np.empty(src.shape, dtype=np.uint8)
    reproject(
        source,
        out,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=DST_TRANSFORM,
        dst_crs="EPSG:3857",
        resampling=method,
    )

    assert np.count_nonzero(out) in expected[method]


@pytest.mark.parametrize(
    "test3d,count_nonzero",
    [
        pytest.param(
            True,
            1309625,
            marks=pytest.mark.skipif(
                gdal_version_info >= (3, 11, 0), reason="See GDAL gh-11713"
            ),
        ),
        pytest.param(
            True,
            1314520,
            marks=pytest.mark.skipif(
                gdal_version_info < (3, 11, 0), reason="See GDAL gh-11713"
            ),
        ),
        pytest.param(
            False,
            437686,
            marks=pytest.mark.skipif(
                gdal_version_info >= (3, 11, 0), reason="See GDAL gh-11713"
            ),
        ),
        pytest.param(
            False,
            438113,
            marks=pytest.mark.skipif(
                gdal_version_info < (3, 11, 0), reason="See GDAL gh-11713"
            ),
        ),
    ],
)
def test_reproject_array_interface(test3d, count_nonzero, path_rgb_byte_tif):
    class DataArray:
        def __init__(self, data):
            self.data = data

        def __array__(self, dtype=None):
            return self.data

        @property
        def dtype(self):
            return self.data.dtype

    with rasterio.open(path_rgb_byte_tif) as src:
        if test3d:
            source = DataArray(src.read())
        else:
            source = DataArray(src.read(1))
    out = DataArray(np.empty(source.data.shape, dtype=np.uint8))
    reproject(
        source,
        out,
        src_transform=src.transform,
        src_crs=src.crs,
        src_nodata=src.nodata,
        dst_transform=DST_TRANSFORM,
        dst_crs="EPSG:3857",
        dst_nodata=99,
    )
    assert isinstance(out, DataArray)
    assert np.count_nonzero(out.data[out.data != 99]) == count_nonzero


@pytest.mark.parametrize(
    "test3d,count_nonzero",
    [
        pytest.param(
            True,
            1308064,
            marks=[
                pytest.mark.skipif(
                    not gdal_version.at_least("3.8"), reason="Requires GDAL 3.8.x"
                ),
                pytest.mark.skipif(
                    gdal_version_info >= (3, 11, 0), reason="See GDAL gh-11713"
                ),
            ],
        ),
        pytest.param(
            True,
            1312959,
            marks=[
                pytest.mark.skipif(
                    not gdal_version.at_least("3.8"), reason="Requires GDAL 3.8.x"
                ),
                pytest.mark.skipif(
                    gdal_version_info < (3, 11, 0), reason="See GDAL gh-11713"
                ),
            ],
        ),
        pytest.param(
            False,
            437686,
            marks=[
                pytest.mark.skipif(
                    not gdal_version.at_least("3.8"), reason="Requires GDAL 3.8.x"
                ),
                pytest.mark.skipif(
                    gdal_version_info >= (3, 11, 0), reason="See GDAL gh-11713"
                ),
            ],
        ),
        pytest.param(
            False,
            438113,
            marks=[
                pytest.mark.skipif(
                    not gdal_version.at_least("3.8"), reason="Requires GDAL 3.8.x"
                ),
                pytest.mark.skipif(
                    gdal_version_info < (3, 11, 0), reason="See GDAL gh-11713"
                ),
            ],
        ),
    ],
)
def test_reproject_masked(test3d, count_nonzero, path_rgb_byte_tif):
    with rasterio.open(path_rgb_byte_tif) as src:
        if test3d:
            source = src.read(masked=True)
        else:
            source = src.read(1, masked=True)
    out = np.empty(source.shape, dtype=np.uint8)
    reproject(
        source,
        out,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=DST_TRANSFORM,
        dst_crs="EPSG:3857",
        dst_nodata=99,
    )
    assert np.ma.is_masked(source)
    assert source.shape == out.shape
    assert np.count_nonzero(out[out != 99]) == count_nonzero
    assert not np.ma.is_masked(out)


@pytest.mark.parametrize(
    "test3d,count_nonzero",
    [
        pytest.param(
            True,
            1312959,
            marks=pytest.mark.skipif(
                not gdal_version.at_least("3.8"), reason="Requires GDAL 3.8.x"
            ),
        ),
        pytest.param(
            False,
            438113,
            marks=pytest.mark.skipif(
                not gdal_version.at_least("3.8"), reason="Requires GDAL 3.8.x"
            ),
        ),
    ],
)
def test_reproject_masked_masked_output(test3d, count_nonzero, path_rgb_byte_tif):
    with rasterio.open(path_rgb_byte_tif) as src:
        if test3d:
            inp = src.read(masked=True)
        else:
            inp = src.read(1, masked=True)
    out = np.ma.masked_array(np.empty(inp.shape, dtype=np.uint8))
    out, _ = reproject(
        inp,
        out,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=DST_TRANSFORM,
        dst_crs="EPSG:3857",
    )
    assert inp.shape == out.shape
    assert np.count_nonzero(out[out != np.ma.masked]) == count_nonzero


@pytest.mark.parametrize(
    "test3d,count_nonzero",
    [
        pytest.param(
            True,
            1309625,
            marks=[
                pytest.mark.skipif(
                    not gdal_version.at_least("3.8"), reason="Requires GDAL 3.8.x"
                ),
                pytest.mark.skipif(
                    gdal_version_info >= (3, 11, 0), reason="See GDAL gh-11713"
                ),
            ],
        ),
        pytest.param(
            True,
            1314520,
            marks=[
                pytest.mark.skipif(
                    not gdal_version.at_least("3.8"), reason="Requires GDAL 3.8.x"
                ),
                pytest.mark.skipif(
                    gdal_version_info < (3, 11, 0), reason="See GDAL gh-11713"
                ),
            ],
        ),
        pytest.param(
            False,
            437686,
            marks=[
                pytest.mark.skipif(
                    not gdal_version.at_least("3.8"), reason="Requires GDAL 3.8.x"
                ),
                pytest.mark.skipif(
                    gdal_version_info >= (3, 11, 0), reason="See GDAL gh-11713"
                ),
            ],
        ),
        pytest.param(
            False,
            438113,
            marks=[
                pytest.mark.skipif(
                    not gdal_version.at_least("3.8"), reason="Requires GDAL 3.8.x"
                ),
                pytest.mark.skipif(
                    gdal_version_info < (3, 11, 0), reason="See GDAL gh-11713"
                ),
            ],
        ),
    ],
)
def test_reproject_masked_no_mask(test3d, count_nonzero, path_rgb_byte_tif):
    with rasterio.open(path_rgb_byte_tif) as src:
        if test3d:
            source = src.read(masked=True)
        else:
            source = src.read(1, masked=True)

    # Fill in the masked values:
    source = np.ma.masked_array(source.filled(), fill_value=source.fill_value)
    assert source.mask is np.ma.nomask

    out = np.empty(source.shape, dtype=np.uint8)
    reproject(
        source,
        out,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=DST_TRANSFORM,
        dst_crs="EPSG:3857",
        dst_nodata=99,
    )
    assert source.shape == out.shape
    assert np.count_nonzero(out[out != 99]) == count_nonzero
    assert not np.ma.is_masked(out)


@pytest.mark.parametrize("method", SUPPORTED_RESAMPLING)
def test_reproject_resampling_alpha(method):
    """Reprojection of a source with alpha band succeeds"""
    # Expected count of nonzero pixels for each resampling method, based
    # on running rasterio with each of the following configurations
    expected = {
        Resampling.nearest: [438113],
        Resampling.bilinear: [439280],
        Resampling.cubic: [437888],
        Resampling.cubic_spline: [440475],
        Resampling.lanczos: [436001],
        Resampling.average: [439172],
        Resampling.mode: [437298, 438002],  # 438002 for GDAL 3.11+.
        Resampling.max: [439464],
        Resampling.min: [436397],
        Resampling.med: [437194],
        Resampling.q1: [436397],
        Resampling.q3: [438948],
        Resampling.sum: [439118, 439142],  # 439142 for GDAL 3.6+
        Resampling.rms: [439385],
    }

    with rasterio.open("tests/data/RGBA.byte.tif") as src:
        source = src.read(1)

    out = np.empty(src.shape, dtype=np.uint8)
    reproject(
        source,
        out,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=DST_TRANSFORM,
        dst_crs="EPSG:3857",
        resampling=method,
    )

    assert np.count_nonzero(out) in expected[method]


def test_reproject_unsupported_resampling():
    """Values not in enums. Resampling are not supported."""
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        source = src.read(1)

    dst_crs = "EPSG:32619"
    out = np.empty(src.shape, dtype=np.uint8)
    with pytest.raises(ValueError):
        reproject(
            source,
            out,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=DST_TRANSFORM,
            dst_crs=dst_crs,
            resampling=99,
        )


def test_reproject_unsupported_resampling_guass():
    """Resampling.gauss is unsupported."""
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        source = src.read(1)

    dst_crs = "EPSG:32619"
    out = np.empty(src.shape, dtype=np.uint8)
    with pytest.raises(ValueError):
        reproject(
            source,
            out,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=DST_TRANSFORM,
            dst_crs=dst_crs,
            resampling=Resampling.gauss,
        )


@pytest.mark.parametrize("method", SUPPORTED_RESAMPLING)
def test_resample_default_invert_proj(method):
    """Nearest and bilinear should produce valid results
    with the default Env
    """

    with rasterio.open("tests/data/world.rgb.tif") as src:
        source = src.read(1)
        profile = src.profile

    dst_crs = "EPSG:32619"

    # Calculate the ideal dimensions and transformation in the new crs
    dst_affine, dst_width, dst_height = calculate_default_transform(
        src.crs, dst_crs, src.width, src.height, *src.bounds
    )

    profile["height"] = dst_height
    profile["width"] = dst_width

    out = np.empty(shape=(dst_height, dst_width), dtype=np.uint8)

    with rasterio.Env():
        reproject(
            source,
            out,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_affine,
            dst_crs=dst_crs,
            resampling=method,
        )

    assert out.mean() > 0


@pytest.mark.xfail(reason="Projection extents have changed with PROJ 8")
def test_target_aligned_pixels():
    """Issue 853 has been resolved"""
    with rasterio.open("tests/data/world.rgb.tif") as src:
        source = src.read(1)
        profile = src.profile

    dst_crs = "EPSG:3857"

    with rasterio.Env(CHECK_WITH_INVERT_PROJ=False):
        # Calculate the ideal dimensions and transformation in the new crs
        dst_affine, dst_width, dst_height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )

        dst_affine, dst_width, dst_height = aligned_target(
            dst_affine, dst_width, dst_height, 10000.0
        )

        profile["height"] = dst_height
        profile["width"] = dst_width

        out = np.empty(shape=(dst_height, dst_width), dtype=np.uint8)

        reproject(
            source,
            out,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_affine,
            dst_crs=dst_crs,
            resampling=Resampling.nearest,
        )

        # Check that there are no black borders
        assert out[:, 0].all()
        assert out[:, -1].all()
        assert out[0, :].all()
        assert out[-1, :].all()


@pytest.mark.parametrize("method", SUPPORTED_RESAMPLING)
def test_resample_no_invert_proj(method):
    """Nearest and bilinear should produce valid results with
    CHECK_WITH_INVERT_PROJ = False
    """

    if method in (
        Resampling.bilinear,
        Resampling.cubic,
        Resampling.cubic_spline,
        Resampling.lanczos,
    ):
        pytest.xfail(
            reason="Some resampling methods succeed but produce blank images. "
            "See https://github.com/rasterio/rasterio/issues/614"
        )

    with rasterio.Env(CHECK_WITH_INVERT_PROJ=False):
        with rasterio.open("tests/data/world.rgb.tif") as src:
            source = src.read(1)
            profile = src.profile.copy()

        dst_crs = "EPSG:32619"

        # Calculate the ideal dimensions and transformation in the new crs
        dst_affine, dst_width, dst_height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )

        profile["height"] = dst_height
        profile["width"] = dst_width

        out = np.empty(shape=(dst_height, dst_width), dtype=np.uint8)

        # see #614, some resampling methods succeed but produce blank images
        out = np.empty(src.shape, dtype=np.uint8)
        reproject(
            source,
            out,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_affine,
            dst_crs=dst_crs,
            resampling=method,
        )

        assert out.mean() > 0


def test_reproject_crs_none():
    """Reproject with crs is None should not cause segfault"""
    src = np.random.random(25).reshape((1, 5, 5))
    srcaff = Affine(1.1, 0.0, 0.0, 0.0, 1.1, 0.0)
    srccrs = None
    dst = np.empty(shape=(1, 11, 11))
    dstaff = Affine(0.5, 0.0, 0.0, 0.0, 0.5, 0.0)
    dstcrs = None

    with pytest.raises(ValueError):
        reproject(
            src,
            dst,
            src_transform=srcaff,
            src_crs=srccrs,
            dst_transform=dstaff,
            dst_crs=dstcrs,
            resampling=Resampling.nearest,
        )


def test_reproject_identity_src():
    """Reproject with an identity like source matrices."""
    src = np.random.random(25).reshape((1, 5, 5))
    dst = np.empty(shape=(1, 10, 10))
    dstaff = Affine(0.5, 0.0, 0.0, 0.0, 0.5, 0.0)
    crs = {"init": "epsg:3857"}

    src_affines = [
        Affine(1.0, 0.0, 0.0, 0.0, 1.0, 0.0),  # Identity both positive
        Affine(1.0, 0.0, 0.0, 0.0, -1.0, 0.0),  # Identity with negative e
    ]

    for srcaff in src_affines:
        # reproject expected to not raise any error in any of the srcaff
        reproject(
            src,
            dst,
            src_transform=srcaff,
            src_crs=crs,
            dst_transform=dstaff,
            dst_crs=crs,
            resampling=Resampling.nearest,
        )


def test_reproject_identity_dst():
    """Reproject with an identity like destination matrices."""
    src = np.random.random(100).reshape((1, 10, 10))
    srcaff = Affine(0.5, 0.0, 0.0, 0.0, 0.5, 0.0)
    dst = np.empty(shape=(1, 5, 5))
    crs = {"init": "epsg:3857"}

    dst_affines = [
        Affine(1.0, 0.0, 0.0, 0.0, 1.0, 0.0),  # Identity both positive
        Affine(1.0, 0.0, 0.0, 0.0, -1.0, 0.0),  # Identity with negative e
    ]

    for dstaff in dst_affines:
        # reproject expected to not raise any error in any of the dstaff
        reproject(
            src,
            dst,
            src_transform=srcaff,
            src_crs=crs,
            dst_transform=dstaff,
            dst_crs=crs,
            resampling=Resampling.nearest,
        )


@pytest.fixture(scope="function")
def rgb_byte_profile():
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        return src.profile


@pytest.mark.parametrize(
    "params", [{"gcps": [0]}, {"rpcs": [0]}, {"src_geoloc_array": (0, 0)}]
)
def test_reproject_src_geoloc_exclusivity(params):
    """Different kinds of source geolocation can't be used together."""
    with pytest.raises(ValueError):
        reproject(1, 1, src_transform=[0], **params)


def test_reproject_gcps(rgb_byte_profile):
    """Reproject using ground control points for the source"""
    source = np.ones((3, 800, 800), dtype=np.uint8) * 255
    out = np.zeros(
        (3, rgb_byte_profile["height"], rgb_byte_profile["height"]), dtype=np.uint8
    )
    src_gcps = [
        GroundControlPoint(row=0, col=0, x=156113, y=2818720, z=0),
        GroundControlPoint(row=0, col=800, x=338353, y=2785790, z=0),
        GroundControlPoint(row=800, col=800, x=297939, y=2618518, z=0),
        GroundControlPoint(row=800, col=0, x=115698, y=2651448, z=0),
    ]
    reproject(
        source,
        out,
        src_crs="EPSG:32618",
        gcps=src_gcps,
        dst_transform=rgb_byte_profile["transform"],
        dst_crs=rgb_byte_profile["crs"],
        resampling=Resampling.nearest,
    )

    assert not out.all()
    assert not out[:, 0, 0].any()
    assert not out[:, 0, -1].any()
    assert not out[:, -1, -1].any()
    assert not out[:, -1, 0].any()


def test_transform_geom_gdal22():
    """Enabling `antimeridian_cutting` has no effect on GDAL 2.2.0 or newer
    where antimeridian cutting is always enabled.  This could produce
    unexpected geometries, so an exception is raised.
    """
    geom = {"type": "Point", "coordinates": [0, 0]}
    with pytest.raises(GDALVersionError):
        transform_geom("EPSG:4326", "EPSG:3857", geom, antimeridian_cutting=False)


def test_issue1056():
    """Warp successfully from RGB's upper bands to an array"""
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        dst_crs = "EPSG:3857"
        out = np.zeros(src.shape, dtype=np.uint8)
        reproject(
            rasterio.band(src, 2),
            out,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=DST_TRANSFORM,
            dst_crs=dst_crs,
            resampling=Resampling.nearest,
        )


def test_reproject_dst_nodata():
    """Affirm resolution of issue #1395"""
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        source = src.read(1)

    dst_crs = "EPSG:3857"
    out = np.empty(src.shape, dtype=np.float32)
    reproject(
        source,
        out,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=DST_TRANSFORM,
        dst_crs=dst_crs,
        src_nodata=0,
        dst_nodata=np.nan,
        resampling=Resampling.nearest,
    )

    assert (out[~np.isnan(out)] > 0.0).sum() == 438113
    assert out[0, 0] != 0
    assert np.isnan(out[0, 0])


def test_issue1401():
    """The warp_mem_limit keyword argument is in effect"""
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        dst_crs = "EPSG:3857"
        out = np.zeros(src.shape, dtype=np.uint8)
        reproject(
            rasterio.band(src, 2),
            out,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=DST_TRANSFORM,
            dst_crs=dst_crs,
            resampling=Resampling.nearest,
            warp_mem_limit=4000,
        )


def test_reproject_dst_alpha(path_rgb_msk_byte_tif):
    """Materialization of external mask succeeds"""

    with rasterio.open(path_rgb_msk_byte_tif) as src:
        nrows, ncols = src.shape

        dst_arr = np.zeros((src.count + 1, nrows, ncols), dtype=np.uint8)

        reproject(
            rasterio.band(src, src.indexes),
            dst_arr,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=DST_TRANSFORM,
            dst_crs="EPSG:3857",
            dst_alpha=4,
        )

        assert dst_arr[3].any()


@pytest.mark.xfail(
    rasterio.__gdal_version__ in ["2.2.0", "2.2.1", "2.2.2", "2.2.3"],
    reason=(
        "GDAL had regression in 2.2.X series, fixed in 2.2.4,"
        " reproject used dst index instead of src index when destination was single band"
    ),
)
def test_issue1350():
    """Warp bands other than 1 or All"""

    with rasterio.open("tests/data/RGB.byte.tif") as src:
        dst_crs = "EPSG:3857"

        reprojected = []

        for dtype, idx in zip(src.dtypes, src.indexes):
            out = np.zeros((1,) + src.shape, dtype=dtype)

            reproject(
                rasterio.band(src, idx),
                out,
                resampling=Resampling.nearest,
                dst_transform=DST_TRANSFORM,
                dst_crs=dst_crs,
            )

            reprojected.append(out)

        for i in range(1, len(reprojected)):
            assert not (reprojected[0] == reprojected[i]).all()


def test_issue_1446():
    """Confirm resolution of #1446"""
    g = transform_geom(
        CRS.from_epsg(4326),
        CRS.from_epsg(32610),
        {"type": "Point", "coordinates": (-122.51403808499907, 38.06106733107932)},
    )
    assert round(g["coordinates"][0], 1) == 542630.9
    assert round(g["coordinates"][1], 1) == 4212702.1


def test_transform_geom_geometry_collection():
    output = transform_geom(
        "EPSG:4326",
        "EPSG:3857",
        {
            "type": "GeometryCollection",
            "geometries": [{"type": "Point", "coordinates": [1, 2]}],
        },
    )
    assert output == {
        "type": "GeometryCollection",
        "geometries": [
            {
                "type": "Point",
                "coordinates": (
                    pytest.approx(111319.49079327357),
                    pytest.approx(222684.20850554405),
                ),
            }
        ],
    }


def test_reproject_init_dest_nodata():
    """No pixels should transfer over"""
    crs = CRS.from_epsg(4326)
    transform = Affine.identity()
    source = np.zeros((1, 100, 100))
    destination = np.ones((1, 100, 100))
    reproject(
        source,
        destination,
        src_crs=crs,
        src_transform=transform,
        dst_crs=crs,
        dst_transform=transform,
        src_nodata=0,
        init_dest_nodata=False,
    )
    assert destination.all()


def test_empty_transform_inputs():
    """Check for fix of #1952"""
    assert ([], []) == rasterio.warp.transform(
        "EPSG:3857", "EPSG:4326", [], [], zs=None
    )


def test_empty_transform_inputs_z():
    """Check for fix of #1952"""
    assert ([], [], []) == rasterio.warp.transform(
        "EPSG:3857", "EPSG:4326", [], [], zs=[]
    )


def test_empty_transform_inputs_length():
    """Get an exception of inputs have different lengths"""
    with pytest.raises(TransformError):
        rasterio.warp.transform("EPSG:3857", "EPSG:4326", [1], [1, 2])


def test_empty_transform_inputs_length_z():
    """Get an exception of inputs have different lengths"""
    with pytest.raises(TransformError):
        rasterio.warp.transform("EPSG:3857", "EPSG:4326", [1, 2], [1, 2], zs=[0])


def test_reproject_rpcs(caplog):
    """Reproject using rational polynomial coefficients for the source"""
    with rasterio.open("tests/data/RGB.byte.rpc.vrt") as src:
        out = np.zeros((3, src.profile["width"], src.profile["height"]), dtype=np.uint8)
        src_rpcs = src.rpcs
        reproject(
            rasterio.band(src, src.indexes),
            out,
            src_crs="EPSG:4326",
            rpcs=src_rpcs,
            dst_crs="EPSG:3857",
            resampling=Resampling.nearest,
        )

        assert not out.all()
        assert not out[:, 0, 0].any()
        assert not out[:, 0, -1].any()
        assert not out[:, -1, -1].any()
        assert not out[:, -1, 0].any()


def test_reproject_rpcs_with_transformer_options(caplog):
    """Reproject using rational polynomial coefficients and additional transformer options"""
    with rasterio.open("tests/data/RGB.byte.rpc.vrt") as src:
        with rasterio.MemoryFile(dirname="foo", filename="dem.tif") as mem:
            crs = 'COMPD_CS["WGS 84 + EGM96 height",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]],VERT_CS["EGM96 height",VERT_DATUM["EGM96 geoid",2005,AUTHORITY["EPSG","5171"]],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Gravity-related height",UP],AUTHORITY["EPSG","5773"]]]'
            transform = Affine(
                0.001953396267361111,
                0.0,
                -124.00013888888888,
                0.0,
                -0.001953396267361111,
                50.000138888888884,
            )
            with mem.open(
                driver="GTiff",
                width=1024,
                height=1024,
                count=1,
                transform=transform,
                dtype="int16",
                crs=crs,
            ) as dem:
                # we flush dem dataset before letting GDAL read from vsimem
                dem.write_band(1, 500 * np.ones((1024, 1024), dtype="int16"))

            out = np.zeros(
                (3, src.profile["width"], src.profile["height"]), dtype=np.uint8
            )
            out2 = out.copy()
            src_rpcs = src.rpcs
            caplog.set_level(logging.DEBUG)
            reproject(
                rasterio.band(src, src.indexes),
                out,
                src_crs="EPSG:4326",
                rpcs=src_rpcs,
                dst_crs="EPSG:3857",
                resampling=Resampling.nearest,
                RPC_DEM=dem.name,
            )
            caplog.set_level(logging.INFO)
            reproject(
                rasterio.band(src, src.indexes),
                out2,
                src_crs="EPSG:4326",
                rpcs=src_rpcs,
                dst_crs="EPSG:3857",
                resampling=Resampling.nearest,
            )

            assert not out.all()
            assert not out2.all()
            assert "RPC_DEM" in caplog.text
            assert not np.array_equal(out, out2)


def test_warp_gcps_compute_dst_transform_automatically_array():
    """Ensure we don't raise an exception when gcps passed without dst_transform, for a source array"""
    source = np.ones((3, 800, 800), dtype=np.uint8) * 255
    out = np.zeros((3, 512, 512))
    src_gcps = [
        GroundControlPoint(row=0, col=0, x=156113, y=2818720, z=0),
        GroundControlPoint(row=0, col=800, x=338353, y=2785790, z=0),
        GroundControlPoint(row=800, col=800, x=297939, y=2618518, z=0),
        GroundControlPoint(row=800, col=0, x=115698, y=2651448, z=0),
    ]
    reproject(
        source,
        out,
        src_crs="EPSG:32618",
        gcps=src_gcps,
        dst_crs="EPSG:32618",
        resampling=Resampling.nearest,
    )

    assert not out.all()
    assert not out[:, 0, 0].any()
    assert not out[:, 0, -1].any()
    assert not out[:, -1, -1].any()
    assert not out[:, -1, 0].any()


def test_warp_gcps_compute_dst_transform_automatically_reader(tmpdir):
    """Ensure we don't raise an exception when gcps passed without dst_transform, for a source dataset"""
    tiffname = str(tmpdir.join("test.tif"))
    src_gcps = [
        GroundControlPoint(row=0, col=0, x=156113, y=2818720, z=0),
        GroundControlPoint(row=0, col=800, x=338353, y=2785790, z=0),
        GroundControlPoint(row=800, col=800, x=297939, y=2618518, z=0),
        GroundControlPoint(row=800, col=0, x=115698, y=2651448, z=0),
    ]
    out = np.zeros((3, 512, 512))

    with rasterio.open(
        tiffname, mode="w", height=800, width=800, count=3, dtype=np.uint8
    ) as source:
        source.gcps = (src_gcps, CRS.from_epsg(32618))

    with rasterio.open(tiffname) as source:
        reproject(
            rasterio.band(source, source.indexes),
            out,
            dst_crs="EPSG:32618",
            resampling=Resampling.nearest,
        )

    assert not out.all()
    assert not out[:, 0, 0].any()
    assert not out[:, 0, -1].any()
    assert not out[:, -1, -1].any()
    assert not out[:, -1, 0].any()


def test_reproject_rpcs_exact_transformer(caplog):
    """Reproject using rational polynomial coefficients and DEM, requiring that
    we don't try to make an approximate transformer.
    """
    with rasterio.open("tests/data/RGB.byte.rpc.vrt") as src:
        with rasterio.MemoryFile(dirname="foo", filename="dem.tif") as mem:
            crs = 'COMPD_CS["WGS 84 + EGM96 height",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]],VERT_CS["EGM96 height",VERT_DATUM["EGM96 geoid",2005,AUTHORITY["EPSG","5171"]],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Gravity-related height",UP],AUTHORITY["EPSG","5773"]]]'
            transform = Affine(
                0.001953396267361111,
                0.0,
                -124.00013888888888,
                0.0,
                -0.001953396267361111,
                50.000138888888884,
            )
            with mem.open(
                driver="GTiff",
                width=1024,
                height=1024,
                count=1,
                transform=transform,
                dtype="int16",
                crs=crs,
            ) as dem:
                # we flush dem dataset before letting GDAL read from vsimem
                dem.write_band(1, 500 * np.ones((1024, 1024), dtype="int16"))

            out = np.zeros(
                (3, src.profile["width"], src.profile["height"]), dtype=np.uint8
            )
            src_rpcs = src.rpcs
            caplog.set_level(logging.DEBUG)
            reproject(
                rasterio.band(src, src.indexes),
                out,
                src_crs="EPSG:4326",
                rpcs=src_rpcs,
                dst_crs="EPSG:3857",
                resampling=Resampling.nearest,
                RPC_DEM=dem.name,
            )

            assert "Created exact transformer" in caplog.text


def test_reproject_rpcs_approx_transformer(caplog):
    """Reproject using rational polynomial coefficients without a DEM, for which it's
    ok to use an approximate transformer.
    """
    with rasterio.open("tests/data/RGB.byte.rpc.vrt") as src:
        out = np.zeros((3, src.profile["width"], src.profile["height"]), dtype=np.uint8)
        src_rpcs = src.rpcs
        caplog.set_level(logging.DEBUG)
        reproject(
            rasterio.band(src, src.indexes),
            out,
            src_crs="EPSG:4326",
            rpcs=src_rpcs,
            dst_crs="EPSG:3857",
            resampling=Resampling.nearest,
        )

        assert "Created approximate transformer" in caplog.text


@pytest.fixture
def http_error_server(data):
    """Serves files from the test data directory, poorly."""
    import functools
    import multiprocessing
    import http.server

    Handler = functools.partial(RangeRequestErrorHandler, directory=str(data))
    httpd = http.server.HTTPServer(("", 0), Handler)
    mp_context = multiprocessing.get_context("fork")
    p = mp_context.Process(target=httpd.serve_forever)
    p.start()
    yield f"{httpd.server_address[0]}:{httpd.server_address[1]}"
    p.terminate()
    p.join()


@pytest.mark.skipif(
    sys.platform != "linux",
    reason="the server fixture requires Linux",
)
def test_reproject_error_propagation(http_error_server, caplog):
    """Propagate errors up from ChunkAndWarpMulti and check for a retry."""

    with rasterio.open(
        f"/vsicurl?max_retry=1&retry_delay=.1&url=http://{http_error_server}/RGB.byte.tif"
    ) as src:
        out = np.zeros((src.count, src.height, src.width), dtype="uint8")

        with pytest.raises(WarpOperationError):
            reproject(
                rasterio.band(src, (1, 2, 3)),
                out,
                dst_crs=src.crs,
                dst_transform=src.transform,
            )

    assert len([rec for rec in caplog.records if "Retrying again" in rec.message]) >= 2


def test_reproject_to_specified_output_bands():
    """
    Reproject multiple input rasters to a single output raster, joining their bands.

    In this example, we concatenate a RGB raster with a mocked NIR image, while reprojecting and resampling both.
    """
    with rasterio.open("tests/data/rgb1.tif") as src_rgb, rasterio.open(
        "tests/data/rgb1_fake_nir_epsg3857.tif"
    ) as src_nir:
        output_crs = CRS.from_epsg(4326)
        output_transform, output_width, output_height = calculate_default_transform(
            src_rgb.crs, output_crs, src_rgb.width, src_rgb.height, *src_rgb.bounds
        )
        with rasterio.MemoryFile() as mem:
            with mem.open(
                driver="GTiff",
                width=output_width,
                height=output_height,
                count=5,
                transform=output_transform,
                dtype="uint8",
                nodata=0,
                crs=output_crs,
            ) as out:  # type: rasterio.io.DatasetWriter
                reproject(
                    rasterio.band(src_rgb, src_rgb.indexes),
                    rasterio.band(out, src_rgb.indexes),
                    resampling=Resampling.nearest,
                )
                reproject(
                    rasterio.band(src_nir, 1),
                    rasterio.band(out, 4),
                    resampling=Resampling.nearest,
                )

            with mem.open() as out:  # type: rasterio.DatasetReader
                assert out.count == 5

                for i in range(1, 5):
                    band_data = out.read(i)
                    assert (band_data != 0).any()

                band_data = out.read(5)
                assert (band_data == 0).all()


def test_rpcs_non_epsg4326():
    with pytest.raises(RPCError):
        with rasterio.open("tests/data/RGB.byte.rpc.vrt") as src:
            src_rpcs = src.rpcs
            reproject(
                rasterio.band(src, src.indexes),
                src_crs="EPSG:3857",
                rpcs=src_rpcs,
                dst_crs="EPSG:4326",
                resampling=Resampling.nearest,
            )


def test_coordinate_pipeline(tmp_path):
    """Transformer COORDINATE_OPERATION option is activated."""
    pipeline = "proj=pipeline step inv proj=utm zone=11 ellps=clrk66 step proj=unitconvert xy_in=rad xy_out=deg step proj=axisswap order=2,1"
    with rasterio.open("tests/data/byte.tif") as src:
        output_transform, output_width, output_height = calculate_default_transform(
            src.crs,
            "EPSG:4326",
            src.width,
            src.height,
            *src.bounds,
            coordinate_operation=pipeline,
        )

        assert output_height == 18
        assert output_width == 22

        profile = src.profile
        profile.update(
            driver="GTiff",
            height=output_height,
            width=output_width,
            transform=output_transform,
            crs="EPSG:4326",
        )
        with rasterio.open(tmp_path.joinpath("test.tif"), "w", **profile) as dst:
            reproject(
                rasterio.band(src, src.indexes),
                rasterio.band(dst, dst.indexes),
                resampling=Resampling.cubic,
                coordinate_operation=pipeline,
            )
            # This is the same value as in GDAL's test_gdalwarp_lib_ct.
            assert dst.checksum(1) == 4705


@pytest.mark.skipif(not gdal_version.at_least("3.6"), reason="Requires GDAL 3.6")
def test_geoloc_warp_dataset(data, tmp_path):
    """Warp a dataset using external geolocation arrays."""
    filename = str(data.join("RGB.byte.tif"))

    # Extract geolocation arrays and create suitable destination dataset.
    with rasterio.open(filename) as src:
        xs, ys = src.transform * np.meshgrid(
            np.arange(src.width), np.arange(src.height)
        )

        profile = src.profile
        profile.update(
            driver="GTiff",
            height=800,
            width=880,
            transform=DST_TRANSFORM,
            crs="EPSG:3857",
        )

    # Now alter the source's geotransform. If the geolocation arrays
    # aren't used, we'll notice.
    with rasterio.open(filename, "r+") as src:
        src.transform = Affine.identity()

    # Reproject the altered source file using provided geolocation
    # arrays.
    with rasterio.open(filename) as src:
        with rasterio.open(tmp_path.joinpath("test.tif"), "w", **profile) as dst:
            reproject(
                rasterio.band(src, src.indexes),
                rasterio.band(dst, dst.indexes),
                src_crs=src.crs,
                src_geoloc_array=np.stack((xs, ys)),
                resampling=Resampling.bilinear,
                num_threads=2,
            )

    with rasterio.open(tmp_path.joinpath("test.tif")) as dst:
        out = dst.read(1)

    # This value is specific to DST_TRANSFORM and an 800 x 880 file.
    assert np.count_nonzero(out) in [464910]


# Before GDAL 3.5.2 geoloc array files aren't recognized and this error
# would be seen from the following tests:
#
# rasterio._err.CPLE_AppDefinedError: The transformation is already
# "north up" or a transformation between pixel/line and georeferenced
# coordinates cannot be computed for
# MEM:::DATAPOINTER=137539856,PIXELS=791,LINES=718,BANDS=3,DATATYPE=Byte.
# There is no affine transformation and no GCPs. Specify transformation
# option SRC_METHOD=NO_GEOTRANSFORM to bypass this check.
@pytest.mark.skipif(not gdal_version.at_least("3.6"), reason="Requires GDAL 3.6")
def test_geoloc_warp_array(path_rgb_byte_tif, tmp_path):
    """Warp an array using external geolocation arrays."""
    with rasterio.open(path_rgb_byte_tif) as src:
        xs, ys = src.transform * np.meshgrid(
            np.arange(src.width), np.arange(src.height)
        )
        source = src.read()

    output = np.zeros((3, 800, 880), dtype="uint8")

    reproject(
        source,
        output,
        src_crs=src.crs,
        src_geoloc_array=np.stack((xs, ys)),
        src_nodata=0,
        dst_transform=DST_TRANSFORM,
        dst_crs="EPSG:3857",
        dst_height=800,
        dst_width=880,
        resampling=Resampling.bilinear,
    )

    # This value is specific to DST_TRANSFORM and an 800 x 880 array.
    assert np.count_nonzero(output[0]) in [464910]


@pytest.mark.skipif(not gdal_version.at_least("3.6"), reason="Requires GDAL 3.6")
def test_geoloc_warp_array_subsampled(path_rgb_byte_tif, tmp_path):
    """Warp an array using subsampled external geolocation arrays."""
    with rasterio.open(path_rgb_byte_tif) as src:
        xs, ys = src.transform * np.meshgrid(
            np.arange(0, src.width, 10), np.arange(0, src.height, 10)
        )
        source = src.read()

    output = np.zeros((3, 800, 880), dtype="uint8")

    reproject(
        source,
        output,
        src_crs=src.crs,
        src_geoloc_array=(xs, ys),
        src_nodata=0,
        dst_transform=DST_TRANSFORM,
        dst_crs="EPSG:3857",
        dst_height=800,
        dst_width=880,
        resampling=Resampling.bilinear,
    )

    # This value is specific to DST_TRANSFORM and an 800 x 880 array.
    assert np.count_nonzero(output[0]) in [471533]

import pytest

import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window

from .conftest import requires_gdal2


@requires_gdal2
def test_float_window(path_rgb_byte_tif):
    """floating point windows work"""
    with rasterio.open(path_rgb_byte_tif) as src:
        out_shape = (401, 401)
        window = Window(300.5, 300.5, 200.5, 200.5)
        src.read(1, window=window, out_shape=out_shape)


@requires_gdal2
@pytest.mark.parametrize(
    "resampling",
    [
        pytest.param(
            Resampling.nearest, marks=pytest.mark.xfail(reason="GDAL issue #3101 affects versions before 3.2.0")
        ),
        Resampling.bilinear,
        Resampling.average,
    ],
)
def test_float_window_fill(path_rgb_byte_tif, resampling):
    """Check on issue 2022"""
    window = Window(20.2, 130.8, 240.3, 450.7)
    with rasterio.open(path_rgb_byte_tif) as src:
        data = src.read(window=window, masked=True, resampling=resampling)

    assert data.mask.sum() == (data.data == data.fill_value).sum()

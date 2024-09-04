"""Colormap tests."""

import rasterio
from rasterio.enums import ColorInterp


def test_write_colormap(tmp_path):
    with rasterio.open("tests/data/shade.tif") as src:
        shade = src.read(1)
        profile = src.profile

    profile["driver"] = "PNG"

    with rasterio.open(tmp_path / "test.tif", "w", **profile) as dst:
        dst.write(shade, indexes=1)
        dst.write_colormap(1, {0: (255, 0, 0, 255), 255: (0, 0, 0, 0)})
        assert dst.colorinterp == (ColorInterp.palette,)
        cmap = dst.colormap(1)
        assert cmap[0] == (255, 0, 0, 255)
        assert cmap[255] == (0, 0, 0, 0)

    with rasterio.open(tmp_path / "test.tif") as src:
        assert src.colorinterp == (ColorInterp.palette,)
        cmap = src.colormap(1)
        assert cmap[0] == (255, 0, 0, 255)
        assert cmap[255] == (0, 0, 0, 0)

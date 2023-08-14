import io

import fsspec

import rasterio

def test_opener_builtin(path_rgb_byte_tif):
    """First test of vsi python plugin opener."""
    with rasterio.open(path_rgb_byte_tif, opener=io.open) as src:
        _ = src.profile


def test_opener_fsspec():
    """First test of vsi python plugin opener."""
    with rasterio.open("zip://*.tif::tests/data/files.zip", opener=fsspec.open) as src:
        _ = src.profile
        print(_)

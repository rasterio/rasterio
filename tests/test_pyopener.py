import io

import rasterio

def test_opener(path_rgb_byte_tif):
    """First test of vsi python plugin opener."""
    with rasterio.open(path_rgb_byte_tif, opener=io.open) as src:
        _ = src.profile

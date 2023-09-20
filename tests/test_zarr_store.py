"""Test of rasterio Zarr store"""

import rasterio
from rasterio.zarr import RasterioStore
import zarr


def test_zarr_store(path_rgb_byte_tif):
    """Open sesame"""
    with rasterio.open(path_rgb_byte_tif) as dataset:
        store = RasterioStore(dataset)
        z = zarr.group(store)
        assert (z["RGB.byte.tif"][:] == dataset.read()).all()

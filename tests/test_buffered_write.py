"""Test of buffered dataset writer."""

import rasterio
import numpy as np
from affine import Affine


def test_no_double_close(tmp_path):
    """Show fix of gh-3064."""
    data = np.zeros((100, 100))
    profile_gtiff = {
        "width": data.shape[0],
        "height": data.shape[1],
        "count": 1,
        "dtype": np.uint8,
        "transform": Affine(3.5, 0.0, 558838.0, 0.0, -3.5, 5927362.0),
        "crs": 32630,
        "nodata": 0,
        "driver": "GTiff",
        "compress": "DEFLATE",
    }
    profile_cog = {
        **profile_gtiff,
        "driver": "COG",
    }
    with tmp_path.joinpath("bar.tiff").open("wb") as fh:
        with rasterio.open(fh, mode="w", **profile_cog) as ds:
            ds.write(data, 1)

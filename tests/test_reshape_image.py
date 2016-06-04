import numpy as np

import rasterio


def test_reshape():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        im_data = rasterio.plot.reshape_as_image(src.read())
        assert im_data.shape == (718, 791, 3)


def test_roundtrip_reshape():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = src.read()
        im_data = rasterio.plot.reshape_as_image(data)
        assert np.array_equal(data, rasterio.plot.reshape_as_raster(im_data))

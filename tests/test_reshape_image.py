import numpy as np

from rasterio import plot
import rasterio

try:
    import matplotlib as mpl
    mpl.use('agg')
except:
    pass

def test_reshape():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        im_data = plot.reshape_as_image(src.read())
        assert im_data.shape == (718, 791, 3)

def test_roundtrip_reshape():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = src.read()
        im_data = plot.reshape_as_image(data)
        assert np.array_equal(data, rasterio.plot.reshape_as_raster(im_data))

def test_reshape_as_raster():
    img_arr = np.random.randn(718L, 791L, 3L)
    rast_arr = plot.reshape_as_raster(img_arr)
    assert img_arr.shape[-1] == rast_arr.shape[0]

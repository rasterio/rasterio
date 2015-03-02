import numpy as np

import rasterio


def test_nodata_range(tmpdir):
    tempfile = str(tmpdir.join('out.tif'))
    data = np.array([[0, 0, 1], [1, 2, 0]])
    kwargs = {
        'driver': u'GTiff',
        'dtype': 'uint8',
        'nodata': -1.7e+308,
        'height': 3,
        'width': 3,
        'count': 1
    }
    with rasterio.drivers():
        with rasterio.open(tempfile, 'w', **kwargs) as dst:
            dst.write_band(1, data.astype(rasterio.uint8))
        with rasterio.open(tempfile) as src:
            data = src.read()
            assert not hasattr(data, 'mask')

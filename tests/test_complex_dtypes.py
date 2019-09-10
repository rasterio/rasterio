import logging
import sys
import uuid

import numpy as np
import pytest

import rasterio


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


@pytest.fixture(scope='function')
def tempfile():
    """A temporary filename in the GDAL '/vsimem' filesystem"""
    return '/vsimem/{}'.format(uuid.uuid4())


def complex_image(height, width, dtype):
    """An array with sequential elements"""
    return np.array(
        [complex(x, x) for x in range(height * width)],
        dtype=dtype).reshape(height, width)

dtypes = ['complex', 'complex64', 'complex128']


@pytest.mark.parametrize("dtype", dtypes)
@pytest.mark.parametrize("height,width", [(20, 20)])
def test_read_array(tempfile, dtype, height, width):
    """_io functions read and write arrays correctly"""
    in_img = complex_image(height, width, dtype)
    with rasterio.open(tempfile, 'w+', driver='GTiff', dtype=dtype,
                       height=height, width=width, count=1) as dataset:
        dataset.write(in_img, 1)
        out_img = dataset.read(1)
    assert (in_img == out_img).all()


def test_complex_nodata(tmpdir):
    """A complex dataset can be created with a real nodata value"""
    import numpy as np
    import rasterio
    from rasterio.transform import Affine

    x = np.linspace(-4.0, 4.0, 240)
    y = np.linspace(-3.0, 3.0, 180)
    X, Y = np.meshgrid(x, y)
    Z1 = np.ones_like(X) + 1j

    res = (x[-1] - x[0]) / 240.0
    transform1 = Affine.translation(x[0] - res / 2, y[-1] - res / 2) * Affine.scale(res, -res)

    tempfile = str(tmpdir.join("test.tif"))
    with rasterio.open(tempfile, 'w', driver='GTiff', height=Z1.shape[0], width=Z1.shape[1], nodata=0, count=1, dtype=Z1.dtype, crs='+proj=latlong', transform=transform1) as dst:
        dst.write(Z1, 1)

    with rasterio.open(tempfile) as dst:
        assert dst.nodata == 0

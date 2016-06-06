
import affine
import numpy as np

import rasterio


def test_pad():
    arr = np.ones((10, 10))
    trans = affine.Affine(1.0, 0.0, 0.0, 0.0, -1.0, 10.0)
    arr2, trans2 = rasterio.pad(arr, trans, 2, 'edge')
    assert arr2.shape == (14, 14)
    assert trans2.xoff == -2.0
    assert trans2.yoff == 12.0

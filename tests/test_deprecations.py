# TODO delete this in 1.0
# This ensures that deprecation warnings are given but behavior is maintained
# on the way to stabilizing the API for 1.0
import warnings

import numpy as np
import pytest

# New modules
import rasterio
from rasterio import windows


DATA_WINDOW = ((3, 5), (2, 6))


@pytest.fixture
def data():
    data = np.zeros((10, 10), dtype='uint8')
    data[slice(*DATA_WINDOW[0]), slice(*DATA_WINDOW[1])] = 1
    return data


def test_mask(recwarn, basic_image_file, basic_geometry):
    from rasterio.mask import mask as mask_new
    from rasterio.tools.mask import mask as mask_old
    nodata_val = 0
    geometries = [basic_geometry]
    with rasterio.open(basic_image_file, "r") as src:
        warnings.simplefilter('once')
        old = mask_old(src, geometries, crop=False,
                       nodata=nodata_val, invert=True)
        recwarn.pop(DeprecationWarning)
        nwarn = len(recwarn)
        new = mask_new(src, geometries, crop=False,
                       nodata=nodata_val, invert=True)
        assert len(recwarn) == nwarn
        for parts in zip(new, old):
            assert np.allclose(parts[0], parts[1])


def test_merge(recwarn, tmpdir):
    from rasterio.merge import merge as merge_new
    from rasterio.tools.merge import merge as merge_old
    inputs = [
        'tests/data/rgb1.tif',
        'tests/data/rgb2.tif',
        'tests/data/rgb3.tif',
        'tests/data/rgb4.tif']
    in_sources = [rasterio.open(x) for x in inputs]
    warnings.simplefilter('always')
    old = merge_old(in_sources)
    recwarn.pop(DeprecationWarning)
    nwarn = len(recwarn)
    new = merge_new(in_sources)
    assert len(recwarn) == nwarn
    for parts in zip(new, old):
        assert np.allclose(parts[0], parts[1])

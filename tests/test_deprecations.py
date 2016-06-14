# TODO delete this in 1.0
# This ensures that deprecation warnings are given but behavior is maintained
# on the way to stabilizing the API for 1.0
import warnings

import numpy as np
import pytest

# New modules
import rasterio
from rasterio import windows

# Deprecated modules
from rasterio import (
    get_data_window, window_intersection, window_union, windows_intersect
)

try:
    import matplotlib as mpl
    mpl.use('agg')
    import matplotlib.pyplot as plt
    plt.show = lambda :None
except:
    pass

DATA_WINDOW = ((3, 5), (2, 6))


@pytest.fixture
def data():
    data = np.zeros((10, 10), dtype='uint8')
    data[slice(*DATA_WINDOW[0]), slice(*DATA_WINDOW[1])] = 1
    return data


def test_data_window_unmasked(data, recwarn):
    warnings.simplefilter('always')
    old = get_data_window(data)
    assert len(recwarn) == 1
    assert recwarn.pop(DeprecationWarning)
    new = windows.get_data_window(data)
    assert len(recwarn) == 0
    assert old == new


def test_windows_intersect_disjunct(recwarn):
    data = [
        ((0, 6), (3, 6)),
        ((2, 4), (1, 5))]
    warnings.simplefilter('always')
    old = windows_intersect(data)
    assert len(recwarn) == 1
    assert recwarn.pop(DeprecationWarning)
    new = windows.intersect(data)
    assert len(recwarn) == 0
    assert old == new


def test_window_intersection(recwarn):
    data = [
        ((0, 6), (3, 6)),
        ((2, 4), (1, 5))]
    warnings.simplefilter('always')
    old = window_intersection(data)
    assert len(recwarn) == 1
    assert recwarn.pop(DeprecationWarning)
    new = windows.intersection(data)
    assert len(recwarn) == 0
    assert old == new


def test_window_union(recwarn):
    data = [
        ((0, 6), (3, 6)),
        ((2, 4), (1, 5))]
    warnings.simplefilter('always')
    old = window_union(data)
    assert len(recwarn) == 1
    assert recwarn.pop(DeprecationWarning)
    new = windows.union(data)
    assert len(recwarn) == 0
    assert old == new


def test_stats(recwarn):
    from rasterio.tool import stats as stats_old
    from rasterio.rio.insp import stats as stats_new
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        warnings.simplefilter('always')
        old = stats_old((src, 1))
        assert len(recwarn) == 1
        assert recwarn.pop(DeprecationWarning)
        new = stats_new((src, 1))
        assert len(recwarn) == 0
        assert np.allclose(np.array(new), np.array(old))


# xfail because for unknown reasons, travis fails with matplotlib errors
@pytest.mark.xfail
def test_show(recwarn):
    from rasterio.tool import show as show_old
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        warnings.simplefilter('always')
        old = show_old((src, 1))
        assert len(recwarn) == 1
        assert recwarn.pop(DeprecationWarning)

        from rasterio.plot import show as show_new
        new = show_new((src, 1))
        assert len(recwarn) == 0
        assert new == old


# xfail because for unknown reasons, travis fails with matplotlib errors
@pytest.mark.xfail
def test_show_hist(recwarn):
    from rasterio.tool import show_hist as show_old
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        warnings.simplefilter('always')
        old = show_old((src, 1))
        assert len(recwarn) == 1
        assert recwarn.pop(DeprecationWarning)

        from rasterio.plot import show_hist as show_new
        new = show_new((src, 1))
        assert len(recwarn) == 0
        assert new == old


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


def test_driver_deprec(recwarn):
    """Test that drivers() still works but raises deprecation
    """
    warnings.simplefilter('always')
    with rasterio.drivers():
        pass
    assert len(recwarn) == 1
    recwarn.pop(DeprecationWarning)
    assert len(recwarn) == 0

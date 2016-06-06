import numpy as np

import rasterio
from rasterio.plot import show, show_hist
from rasterio.rio.insp import stats

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


def test_stats():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        results = stats((src, 1))
        assert results[0] == 0
        assert results[1] == 255
        assert np.isclose(results[2], 29.9477)

        results2 = stats(src.read(1))
        assert np.allclose(np.array(results), np.array(results2))


def test_show_raster():
    """
    This test only verifies that code up to the point of plotting with
    matplotlib works correctly.  Tests do not exercise matplotlib.
    """
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        try:
            show((src, 1))
            fig = plt.gcf()
            plt.close(fig)
        except ImportError:
            pass


def test_show_raster_no_bounds():
    """
    This test only verifies that code up to the point of plotting with
    matplotlib works correctly.  Tests do not exercise matplotlib.
    """
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        try:
            show((src, 1), with_bounds=False)
            fig = plt.gcf()
            plt.close(fig)
        except ImportError:
            pass


def test_show_array():
    """
    This test only verifies that code up to the point of plotting with
    matplotlib works correctly.  Tests do not exercise matplotlib.
    """
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        try:
            show(src.read(1))
            fig = plt.gcf()
            plt.close(fig)
        except ImportError:
            pass


def test_show_hist():
    """
    This test only verifies that code up to the point of plotting with
    matplotlib works correctly.  Tests do not exercise matplotlib.
    """
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        try:
            show_hist((src, 1), bins=256)
            fig = plt.gcf()
            plt.close(fig)
        except ImportError:
            pass

        try:
            show_hist(src.read(), bins=256)
            fig = plt.gcf()
            plt.close(fig)
        except ImportError:
            pass

import numpy as np
import pytest

try:
    import matplotlib as mpl
    mpl.use('agg')
    import matplotlib.pyplot as plt
    plt.show = lambda :None
except ImportError:
    plt = None

import rasterio
from rasterio.plot import show, show_hist, get_plt

@pytest.mark.skipif(plt is None,
                    reason="requires matplotlib")
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

@pytest.mark.skipif(plt is None,
                    reason="requires matplotlib")
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

@pytest.mark.skipif(plt is None,
                    reason="requires matplotlib")
def test_show_raster_cmap():
    """
    This test only verifies that code up to the point of plotting with
    matplotlib works correctly.  Tests do not exercise matplotlib.
    """
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        try:
            show((src, 1), cmap='jet')
            fig = plt.gcf()
            plt.close(fig)
        except ImportError:
            pass

@pytest.mark.skipif(plt is None,
                    reason="requires matplotlib")
def test_show_raster_ax():
    """
    This test only verifies that code up to the point of plotting with
    matplotlib works correctly.  Tests do not exercise matplotlib.
    """
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        try:
            fig, ax = plt.subplots(1)
            show((src, 1), ax=ax)
            fig = plt.gcf()
            plt.close(fig)
        except ImportError:
            pass

@pytest.mark.skipif(plt is None,
                    reason="requires matplotlib")
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

@pytest.mark.skipif(plt is None,
                    reason="requires matplotlib")
def test_show_array3D():
    """
    This test only verifies that code up to the point of plotting with
    matplotlib works correctly.  Tests do not exercise matplotlib.
    """
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        try:
            show(src.read((1, 2, 3)))
            fig = plt.gcf()
            plt.close(fig)
        except ImportError:
            pass

@pytest.mark.skipif(plt is None,
                    reason="requires matplotlib")
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

@pytest.mark.skipif(plt is None,
                    reason="requires matplotlib")
def test_show_hist_mplargs():
    """
    This test only verifies that code up to the point of plotting with
    matplotlib works correctly.  Tests do not exercise matplotlib.
    """
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        try:
            show_hist(src, bins=50, lw=0.0, stacked=False, alpha=0.3, 
               histtype='stepfilled', title="World Histogram overlaid")
            fig = plt.gcf()
            plt.close(fig)
        except ImportError:
            pass

@pytest.mark.skipif(plt is None,
                    reason="requires matplotlib")
def test_show_contour():
    """
    This test only verifies that code up to the point of plotting with
    matplotlib works correctly.  Tests do not exercise matplotlib.
    """
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        try:
            show((src, 1), contour=True)
            fig = plt.gcf()
            plt.close(fig)
        except ImportError:
            pass

@pytest.mark.skipif(plt is None,
                    reason="requires matplotlib")
def test_show_contour_mplargs():
    """
    This test only verifies that code up to the point of plotting with
    matplotlib works correctly.  Tests do not exercise matplotlib.
    """
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        try:
            show((src, 1), contour=True, 
                levels=[25, 125], colors=['white', 'red'], linewidths=4,
                contour_label_kws=dict(fontsize=18, fmt="%1.0f", inline_spacing=15, use_clabeltext=True))
            fig = plt.gcf()
            plt.close(fig)
        except ImportError:
            pass

@pytest.mark.skipif(plt is None,
                    reason="requires matplotlib")
def test_get_plt():
    """
    This test only verifies that code up to the point of plotting with
    matplotlib works correctly.  Tests do not exercise matplotlib.
    """
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        try:
            assert plt == get_plt()
        except ImportError:
            pass
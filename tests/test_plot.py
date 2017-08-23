"""Unittests for rasterio.plot"""


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
from rasterio.plot import show, show_hist, get_plt, plotting_extent
from rasterio.enums import ColorInterp


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

    with rasterio.open('tests/data/RGB.byte.tif') as src:
        try:
            show((src, (1, 2, 3)))
            fig = plt.gcf()
            plt.close(fig)

        except ImportError:
            pass

    with rasterio.open('tests/data/RGB.byte.tif') as src:
        try:
            show(src)
            fig = plt.gcf()
            plt.close(fig)
        except ImportError:
            pass

    with rasterio.open('tests/data/float.tif') as src:
        try:
            show(src)
            fig = plt.gcf()
            plt.close(fig)
        except ImportError:
            pass

def test_show_cmyk_interp(tmpdir):
    """A CMYK TIFF has cyan, magenta, yellow, black bands."""
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        meta = src.meta
    meta['photometric'] = 'CMYK'
    meta['count'] = 4
    tiffname = str(tmpdir.join('foo.tif'))
    with rasterio.open(tiffname, 'w', **meta) as dst:
        assert dst.profile['photometric'] == 'cmyk'
        assert dst.colorinterp(1) == ColorInterp.cyan
        assert dst.colorinterp(2) == ColorInterp.magenta
        assert dst.colorinterp(3) == ColorInterp.yellow
        assert dst.colorinterp(4) == ColorInterp.black

    with rasterio.open(tiffname) as src:
        try:
            show(src)
            fig = plt.gcf()
            plt.close(fig)
        except ImportError:
            pass

@pytest.mark.skipif(plt is None, reason="requires matplotlib")
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


@pytest.mark.skipif(plt is None, reason="requires matplotlib")
def test_show_raster_title():
    """
    This test only verifies that code up to the point of plotting with
    matplotlib works correctly.  Tests do not exercise matplotlib.
    """
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        try:
            show((src, 1), title="insert title here")
            fig = plt.gcf()
            plt.close(fig)
        except ImportError:
            pass

@pytest.mark.skipif(plt is None, reason="requires matplotlib")
def test_show_hist_large():
    """
    This test only verifies that code up to the point of plotting with
    matplotlib works correctly.  Tests do not exercise matplotlib.
    """
    try:
        rand_arr = np.random.randn(10, 718, 791)
        show_hist(rand_arr)
        fig = plt.gcf()
        plt.close(fig)
    except ImportError:
        pass

@pytest.mark.skipif(plt is None, reason="requires matplotlib")
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

@pytest.mark.skipif(plt is None, reason="requires matplotlib")
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

@pytest.mark.skipif(plt is None, reason="requires matplotlib")
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


@pytest.mark.skipif(plt is None, reason="requires matplotlib")
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

@pytest.mark.skipif(plt is None, reason="requires matplotlib")
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

        try:
            fig, ax = plt.subplots(1)
            show_hist(src.read(), bins=256, ax=ax)
            fig = plt.gcf()
            plt.close(fig)
        except ImportError:
            pass

@pytest.mark.skipif(plt is None, reason="requires matplotlib")
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

@pytest.mark.skipif(plt is None, reason="requires matplotlib")
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

@pytest.mark.skipif(plt is None, reason="requires matplotlib")
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

@pytest.mark.skipif(plt is None, reason="requires matplotlib")
def test_get_plt():
    """
    This test only verifies that code up to the point of plotting with
    matplotlib works correctly.  Tests do not exercise matplotlib.
    """
    with rasterio.open('tests/data/RGB.byte.tif'):
        try:
            assert plt == get_plt()
        except ImportError:
            pass

@pytest.mark.skipif(plt is None, reason="requires matplotlib")
def test_plt_transform():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        show(src.read(), transform=src.transform)
        show(src.read(1), transform=src.transform)

def test_plotting_extent():
    from rasterio.plot import reshape_as_image
    expected = (101985.0, 339315.0, 2611485.0, 2826915.0)
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert plotting_extent(src) == expected
        assert plotting_extent(
            reshape_as_image(src.read()), transform=src.affine) == expected
        assert plotting_extent(
            src.read(1), transform=src.transform) == expected
        # array requires a transform
        with pytest.raises(ValueError):
            plotting_extent(src.read(1))

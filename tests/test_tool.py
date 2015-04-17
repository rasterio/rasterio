import numpy as np

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

import rasterio
from rasterio.tool import show, stats


def test_stats():
    with rasterio.drivers():
        with rasterio.open('tests/data/RGB.byte.tif') as src:
            results = stats((src, 1))
            assert results[0] == 0
            assert results[1] == 255
            assert np.isclose(results[2], 29.9477)

            results2 = stats(src.read(1))
            assert np.allclose(np.array(results), np.array(results2))


def test_show():
    """
    This test only verifies that code up to the point of plotting with
    matplotlib works correctly.  Tests do not exercise matplotlib.
    """
    if plt:
        # Return because plotting causes the tests to block until the plot
        # window is closed.
        return

    with rasterio.drivers():
        with rasterio.open('tests/data/RGB.byte.tif') as src:
            try:
                show((src, 1))
            except ImportError:
                pass

            try:
                show(src.read(1))
            except ImportError:
                pass

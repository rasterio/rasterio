"""Implementations of various common operations.

Including `show()` for displaying an array or with matplotlib.
Most can handle a numpy array or `rasterio.Band()`.
Primarily supports `$ rio insp`.
"""

from __future__ import absolute_import

import logging
import warnings

import numpy as np

import rasterio
from rasterio.compat import zip_longest

try:
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover
    plt = None
except RuntimeError as e:  # pragma: no cover
    # Certain environment configurations can trigger a RuntimeError like:

    # Trying to import matplotlibRuntimeError: Python is not installed as a
    # framework. The Mac OS X backend will not be able to function correctly
    # if Python is not installed as a framework. See the Python ...
    warnings.warn(str(e), RuntimeWarning, stacklevel=2)
    plt = None



logger = logging.getLogger(__name__)


def show(source, cmap='gray', with_bounds=True):
    """Display a raster or raster band using matplotlib.

    Parameters
    ----------
    source : array-like or (raster dataset, bidx)
        If array-like, should be of format compatible with
        matplotlib.pyplot.imshow. If the tuple (raster dataset, bidx),
        selects band `bidx` from raster.
    cmap : str (opt)
        Specifies the colormap to use in plotting. See
        matplotlib.Colors.Colormap. Default is 'gray'.
    with_bounds : bool (opt)
        Whether to change the image extent to the spatial bounds of the image,
        rather than pixel coordinates. Only works when source is
        (raster dataset, bidx).
    """
    if isinstance(source, tuple):
        arr = source[0].read(source[1])
        if with_bounds:
            extent = plotting_extent(source[0])
        else:
            extent = None
    else:
        arr = source
        extent = None
    if plt is not None:
        plt.imshow(arr, cmap=cmap, extent=extent)
        fig = plt.gcf()
        fig.show()
    else:  # pragma: no cover
        raise ImportError("matplotlib could not be imported")


def plotting_extent(source):
    """Returns an extent in the format needed
     for matplotlib's imshow (left, right, bottom, top)
     instead of rasterio's bounds (left, bottom, top, right)

    Parameters
    ----------
    source : raster dataset
    """
    extent = (source.bounds.left, source.bounds.right,
              source.bounds.bottom, source.bounds.top)
    return extent


def reshape_as_image(arr):
    """Returns the source array reshaped into the order
    expected by image processing and visualization software
    (matplotlib, scikit-image, etc)
    by swapping the axes order from (bands, rows, columns)
    to (rows, columns, bands)

    Parameters
    ----------
    source : array-like in a of format (bands, rows, columns)
    """
    # swap the axes order from (bands, rows, columns) to (rows, columns, bands)
    im = np.transpose(arr, [1,2,0])
    return im


def reshape_as_raster(arr):
    """Returns the array in a raster order
    by swapping the axes order from (rows, columns, bands)
    to (bands, rows, columns)

    Parameters
    ----------
    arr : array-like in the image form of (rows, columns, bands)
    """
    # swap the axes order from (rows, columns, bands) to (bands, rows, columns)
    im = np.transpose(arr, [2,0,1])
    return im


def show_hist(source, bins=10, masked=True, title='Histogram'):
    """Easily display a histogram with matplotlib.

    Parameters
    ----------
    bins : int, optional
        Compute histogram across N bins.
    data : np.array or rasterio.Band or tuple(dataset, bidx)
        Input data to display.  The first three arrays in multi-dimensional
        arrays are plotted as red, green, and blue.
    masked : bool, optional
        When working with a `rasterio.Band()` object, specifies if the data
        should be masked on read.
    title : str, optional
        Title for the figure.
    """
    if plt is None:  # pragma: no cover
        raise ImportError("Could not import matplotlib")

    if isinstance(source, (tuple, rasterio.Band)):
        arr = source[0].read(source[1], masked=masked)
    else:
        arr = source

    # The histogram is computed individually for each 'band' in the array
    # so we need the overall min/max to constrain the plot
    rng = arr.min(), arr.max()

    if len(arr.shape) is 2:
        arr = [arr]
        colors = ['gold']
    else:
        colors = ('red', 'green', 'blue', 'violet', 'gold', 'saddlebrown')

    # If a rasterio.Band() is given make sure the proper index is displayed
    # in the legend.
    if isinstance(source, (tuple, rasterio.Band)):
        labels = [str(source[1])]
    else:
        labels = (str(i + 1) for i in range(len(arr)))

    # This loop should add a single plot each band in the input array,
    # regardless of if the number of bands exceeds the number of colors.
    # The colors slicing ensures that the number of iterations always
    # matches the number of bands.
    # The goal is to provide a curated set of colors for working with
    # smaller datasets and let matplotlib define additional colors when
    # working with larger datasets.
    for bnd, color, label in zip_longest(arr, colors[:len(arr)], labels):

        plt.hist(
            bnd.flatten(),
            bins=bins,
            alpha=0.5,
            color=color,
            label=label,
            range=rng
        )

    plt.legend(loc="upper right")
    plt.title(title, fontweight='bold')
    plt.grid(True)
    plt.xlabel('DN')
    plt.ylabel('Frequency')
    fig = plt.gcf()
    fig.show()

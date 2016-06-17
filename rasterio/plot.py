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
from rasterio._io import RasterReader
from rasterio.transform import guard_transform
from rasterio.compat import zip_longest

logger = logging.getLogger(__name__)


def get_plt():
    """import matplotlib.pyplot
    raise import error if matplotlib is not installed
    """
    try:
        import matplotlib.pyplot as plt
        return plt
    except (ImportError, RuntimeError):  # pragma: no cover
        msg = "Could not import matplotlib\n"
        msg += "matplotlib required for plotting functions"
        raise ImportError(msg)


def show(source, with_bounds=True, contour=False, contour_label_kws=None,
         ax=None, title=None,  **kwargs):
    """Display a raster or raster band using matplotlib.

    Parameters
    ----------
    source : GeoArray,
        or (raster dataset, bidx) tuple,
        or raster dataset,
        If the tuple (raster dataset, bidx),
        selects band `bidx` from raster.  If raster dataset display the rgb image
        as defined in the colorinterp metadata, or default to first band.
    with_bounds : bool (opt)
        Whether to change the image extent to the spatial bounds of the image,
        rather than pixel coordinates. Only works when source is
        (raster dataset, bidx) or raster dataset.
    contour : bool (opt)
        Whether to plot the raster data as contours
    contour_label_kws : dictionary (opt)
        Keyword arguments for labeling the contours,
        empty dictionary for no labels.
    ax : matplotlib axis (opt)
        Axis to plot on, otherwise uses current axis.
    title : str, optional
        Title for the figure.
    **kwargs : key, value pairings optional
        These will be passed to the matplotlib imshow or contour method
        depending on contour argument.
        See full lists at:
        http://matplotlib.org/api/axes_api.html?highlight=imshow#matplotlib.axes.Axes.imshow
        or
        http://matplotlib.org/api/axes_api.html?highlight=imshow#matplotlib.axes.Axes.contour

    Returns
    -------
    ax : matplotlib Axes
        Axes with plot.
    """
    plt = get_plt()

    if isinstance(source, tuple):
        arr = source[0].read(source[1])
        if with_bounds:
            kwargs['extent'] = plotting_extent(source[0])
    elif isinstance(source, RasterReader):
        if source.count == 1:
            arr = source.read(1, masked=True)
        else:
            try:
                source_colorinterp = {source.colorinterp(n): n for n in source.indexes}
                colorinterp = rasterio.enums.ColorInterp
                rgb_indexes = [source_colorinterp[ci] for ci in
                               (colorinterp.red, colorinterp.green, colorinterp.blue)]
                arr = source.read(rgb_indexes, masked=True)
                arr = reshape_as_image(arr)

                if with_bounds:
                    kwargs['extent'] = plotting_extent(source)
            except KeyError:
                arr = source.read(1, masked=True)
    else:
        # The source is a GeoArray, reshape its data to image if it has 3+ bands
        arr = np.ma.squeeze(source.image)
        if len(arr.shape) >= 3:
            arr = reshape_as_image(arr)
        if with_bounds:
            kwargs['extent'] = plotting_extent(source)

    show = False
    if not ax:
        show = True
        ax = plt.gca()

    if contour:
        if 'cmap' not in kwargs:
            kwargs['colors'] = kwargs.get('colors', 'red')
        kwargs['linewidths'] = kwargs.get('linewidths', 1.5)
        kwargs['alpha'] = kwargs.get('alpha', 0.8)

        C = ax.contour(arr, origin='upper', **kwargs)
        if contour_label_kws is None:
            # no explicit label kws passed use defaults
            contour_label_kws = dict(fontsize=8,
                                     inline=True)
        if contour_label_kws:
            ax.clabel(C, **contour_label_kws)
    else:
        ax.imshow(arr, **kwargs)
    if title:
        ax.set_title(title, fontweight='bold')

    if show:
        plt.show()

    return ax


def plotting_extent(source):
    """Returns an extent in the format needed
     for matplotlib's imshow (left, right, bottom, top)
     instead of rasterio's bounds (left, bottom, top, right)

    Parameters
    ----------
    source : raster dataset or GeoArray
    transform: Affine, required if source is array
    """
    if not hasattr(source, 'bounds'):
        raise ValueError('Source must have a bounds attribute')

    return (source.bounds.left, source.bounds.right,
            source.bounds.bottom, source.bounds.top)


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
    im = np.ma.transpose(arr, [1,2,0])
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


def show_hist(source, bins=10, masked=True, title='Histogram', ax=None, **kwargs):
    """Easily display a histogram with matplotlib.

    Parameters
    ----------
    source : np.array or RasterReader, rasterio.Band or tuple(dataset, bidx)
        Input data to display.  The first three arrays in multi-dimensional
        arrays are plotted as red, green, and blue.
    bins : int, optional
        Compute histogram across N bins.
    masked : bool, optional
        When working with a `rasterio.Band()` object, specifies if the data
        should be masked on read.
    title : str, optional
        Title for the figure.
    ax : matplotlib axes (opt)
        The raster will be added to this axes if passed.
    **kwargs : optional keyword arguments
        These will be passed to the matplotlib hist method. See full list at:
        http://matplotlib.org/api/axes_api.html?highlight=imshow#matplotlib.axes.Axes.hist
    """
    plt = get_plt()

    if isinstance(source, RasterReader):
        arr = source.read(masked=masked)
    elif isinstance(source, (tuple, rasterio.Band)):
        arr = source[0].read(source[1], masked=masked)
    else:
        arr = source

    # The histogram is computed individually for each 'band' in the array
    # so we need the overall min/max to constrain the plot
    rng = arr.min(), arr.max()

    if len(arr.shape) is 2:
        arr = np.expand_dims(arr.flatten(), 0).T
        colors = ['gold']
    else:
        arr = arr.reshape(arr.shape[0], -1).T
        colors = ['red', 'green', 'blue', 'violet', 'gold', 'saddlebrown']

    # The goal is to provide a curated set of colors for working with
    # smaller datasets and let matplotlib define additional colors when
    # working with larger datasets.
    if arr.shape[-1] > len(colors):
        n = arr.shape[-1] - len(colors)
        colors.extend(np.ndarray.tolist(plt.get_cmap('Accent')(np.linspace(0, 1, n))))
    else:
        colors = colors[:arr.shape[-1]]

    # If a rasterio.Band() is given make sure the proper index is displayed
    # in the legend.
    if isinstance(source, (tuple, rasterio.Band)):
        labels = [str(source[1])]
    else:
        labels = (str(i + 1) for i in range(len(arr)))

    if ax:
        show = False
    else:
        show = True
        ax = plt.gca()

    fig = ax.get_figure()

    ax.hist(arr,
            bins=bins,
            color=colors,
            label=labels,
            range=rng,
            **kwargs)

    ax.legend(loc="upper right")
    ax.set_title(title, fontweight='bold')
    ax.grid(True)
    ax.set_xlabel('DN')
    ax.set_ylabel('Frequency')
    if show:
        plt.show()

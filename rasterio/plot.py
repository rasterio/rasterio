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
   

def show(source, cmap='gray', with_bounds=True, ax=None, title=None, **kwargs):
    """Display a raster or raster band using matplotlib.

    Parameters
    ----------
    source : array-like, or (raster dataset, bidx) tuple, or raster dataset, 
        If array-like, should be of format compatible with
        matplotlib.pyplot.imshow. If the tuple (raster dataset, bidx),
        selects band `bidx` from raster.  If raster dataset display the rgb image 
        as defined in the colorinterp metadata, or default to first band. 
    cmap : str (opt)
        Specifies the colormap to use in plotting. See
        matplotlib.Colors.Colormap. Default is 'gray'.
    with_bounds : bool (opt)
        Whether to change the image extent to the spatial bounds of the image,
        rather than pixel coordinates. Only works when source is
        (raster dataset, bidx) or raster dataset.
    ax : matplotlib axes (opt)
        The raster will be added to this axes if passed.
    title : str, optional
        Title for the figure.
    **kwargs : optional keyword arguments
        These will be passed to the matplotlib imshow method. See full list at:
        http://matplotlib.org/api/axes_api.html?highlight=imshow#matplotlib.axes.Axes.imshow
    """
    plt = get_plt()
        
    if isinstance(source, tuple):
        arr = source[0].read(source[1])
        if with_bounds:
            kwargs['extent'] = plotting_extent(source[0])
    elif  isinstance(source, rasterio._io.RasterReader):
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
        arr = source

    if ax:
        ax.imshow(arr, cmap=cmap, **kwargs)
        if title:
            ax.set_title(title, fontweight='bold')
        return ax
    else:
        plt.imshow(arr, cmap=cmap, **kwargs)
        if title:
            plt.title(title, fontweight='bold')
        ax = plt.gca()
        plt.show()



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
    source : np.array or rasterio._io.RasterReader, rasterio.Band or tuple(dataset, bidx)
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

    if isinstance(source, rasterio._io.RasterReader):
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

    #The goal is to provide a curated set of colors for working with
    # smaller datasets and let matplotlib define additional colors when
    # working with larger datasets.
    if arr.shape[-1] > len(colors):
        n = arr.shape[-1] - len(colors)
        colors.append(mpl.cm.Accent(np.linspace(0, 1, n)))
    else:
        colors = colors[:arr.shape[-1]]

    # If a rasterio.Band() is given make sure the proper index is displayed
    # in the legend.
    if isinstance(source, (tuple, rasterio.Band)):
        labels = [str(source[1])]
    else:
        labels = (str(i + 1) for i in range(len(arr)))

    if ax:
        show = True
    else:
        show = False
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
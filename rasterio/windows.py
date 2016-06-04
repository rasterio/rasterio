"""Windows and related functions."""

import collections
import functools


def iter_args(function):
    """Decorator to allow function to take either *args or
    a single iterable which gets expanded to *args.
    """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        if len(args) == 1 and isinstance(args[0], collections.Iterable):
            return function(*args[0])
        else:
            return function(*args)
    return wrapper


def get_data_window(arr, nodata=None):
    """Return a window for the non-nodata pixels within the input array.

    Parameters
    ----------
    arr: numpy ndarray, <= 3 dimensions
    nodata: number
        If None, will either return a full window if arr is not a masked
        array, or will use the mask to determine non-nodata pixels.
        If provided, it must be a number within the valid range of the dtype
        of the input array.

    Returns
    -------
    ((row_start, row_stop), (col_start, col_stop))

    """
    from rasterio._io import get_data_window
    return get_data_window(arr, nodata)


@iter_args
def union(*windows):
    """Union windows and return the outermost extent they cover.

    Parameters
    ----------
    windows: list-like of window objects
        ((row_start, row_stop), (col_start, col_stop))

    Returns
    -------
    ((row_start, row_stop), (col_start, col_stop))
    """
    from rasterio._io import window_union
    return window_union(windows)


@iter_args
def intersection(*windows):
    """Intersect windows and return the innermost extent they cover.

    Will raise ValueError if windows do not intersect.

    Parameters
    ----------
    windows: list-like of window objects
        ((row_start, row_stop), (col_start, col_stop))

    Returns
    -------
    ((row_start, row_stop), (col_start, col_stop))
    """
    from rasterio._io import window_intersection
    return window_intersection(windows)


@iter_args
def intersect(*windows):
    """Test if windows intersect.

    Parameters
    ----------
    windows: list-like of window objects
        ((row_start, row_stop), (col_start, col_stop))

    Returns
    -------
    boolean:
        True if all windows intersect.
    """
    from rasterio._io import windows_intersect
    return windows_intersect(windows)

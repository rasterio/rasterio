# Workaround for issue #378. A pure Python generator.

import numpy as np
import operator
from functools import partial
from collections import defaultdict
from itertools import zip_longest

import rasterio._loading
with rasterio._loading.add_gdal_dll_directories():
    from rasterio.enums import MaskFlags
    from rasterio.windows import Window
    from rasterio.transform import rowcol


def _grouper(iterable, n, fillvalue=None):
    "Collect data into non-overlapping fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    # from itertools recipes
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)
    

def transform_xy(dataset, xy):
    notNone = partial(operator.is_not, None)
    dt = dataset.transform
    rv = []
    for pts in _grouper(xy, 256):
        pts = zip(*filter(notNone, pts))
        rv.extend(zip(*rowcol(dt, *pts)))
    return rv


def sample_gen(dataset, xy, indexes=None, masked=False):
    """Sample pixels from a dataset

    Parameters
    ----------
    dataset : rasterio Dataset
        Opened in "r" mode.
    xy : iterable
        Pairs of x, y coordinates in the dataset's reference system.
    indexes : int or list of int
        Indexes of dataset bands to sample.
    masked : bool, default: False
        Whether to mask samples that fall outside the extent of the
        dataset.
    sort : bool, default: False
        Sort coordinates for hopefully better performance.
        This will hold all the points in memory at once and may be
        memory intensive.

    Yields
    ------
    array
        A array of length equal to the number of specified indexes
        containing the dataset values for the bands corresponding to
        those indexes.

    """
    read = dataset.read
    height = dataset.height
    width = dataset.width

    if indexes is None:
        indexes = dataset.indexes
    elif isinstance(indexes, int):
        indexes = [indexes]

    nodata = np.full(len(indexes), (dataset.nodata or 0),  dtype=dataset.dtypes[0])
    if masked:
        # Masks for masked arrays are inverted (False means valid)
        mask = [MaskFlags.all_valid not in dataset.mask_flag_enums[i-1] for i in indexes]
        nodata = np.ma.array(nodata, mask=mask)

    # Intermediate conversion to row/col coordinates
    samples = transform_xy(dataset, xy)

    # group access by block
    sorted_samples = np.lexsort(list(reversed(tuple(zip(*samples)))))
    for i in sorted_samples:
        row, col = samples[i]
        if 0 <= row < height and 0 <= col < width:
            win = Window(col, row, 1, 1)
            data = read(indexes, window=win, masked=masked)
            samples[i] = data[:, 0, 0]
        else:
            samples[i] = nodata
    return samples

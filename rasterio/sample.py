# Workaround for issue #378. A pure Python generator.

import numpy as np
import operator
from functools import partial
from collections import defaultdict
from itertools import chain

import rasterio._loading
with rasterio._loading.add_gdal_dll_directories():
    from rasterio.enums import MaskFlags
    from rasterio.windows import Window
    from rasterio.transform import rowcol

from itertools import zip_longest

def _grouper(iterable, n, fillvalue=None):
    "Collect data into non-overlapping fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    # from itertools recipes
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def get_block(dataset, row, col):
    bshapes = dataset.block_shapes
    if len(bshapes) > 0:
        xs, ys = bshapes[0]
        return (divmod(row, xs), divmod(col, ys))
    else:
        raise RuntimeError


def groupby_block(dataset, xy):
    block_map = defaultdict(list)
    for i, pt in enumerate(xy):
        block = get_block(dataset, *pt)
        blocknum = (block[0][0], block[1][0])
        blockcoord = (block[0][1], block[1][1])
        block_map[dataset.block_window(1, *blocknum)].append((i, blockcoord))
    block_map.default_factory = None
    return block_map

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
    block_map = groupby_block(dataset, samples)
    for win, pixels in block_map.items():
        data = read(indexes, window=win, masked=masked)
        for (i, pixel) in pixels:
            if pixel[0] >= data.shape[-2] or pixel[1] >= data.shape[-1]:
                samples[i] = nodata
            else:
                samples[i] = data[:, pixel[0], pixel[1]]

    return samples

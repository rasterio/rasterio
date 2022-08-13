# Workaround for issue #378. A pure Python generator.

import numpy as np
from collections import defaultdict
from itertools import islice, chain

import rasterio._loading
with rasterio._loading.add_gdal_dll_directories():
    from rasterio.enums import MaskFlags
    from rasterio.windows import Window
    from rasterio.transform import rowcol


def groupby_block(dataset, xy):
    def get_block(dataset, row, col):
        bshapes = dataset.block_shapes
        if len(bshapes) > 0:
            xs, ys = bshapes[0]
            return (divmod(row, xs), divmod(col, ys))
        else:
            raise RuntimeError

    block_map = defaultdict(list)
    for i, pt in enumerate(xy):
        block = get_block(dataset, *pt)
        blocknum = (block[0][0], block[1][0])
        block_map[dataset.block_window(1, *blocknum)].append(i)
    return list(chain.from_iterable(block_map.values()))


def transform_xy(dataset, xy):
    dt = dataset.transform
    rv = []
    _xy = iter(xy)
    while True:
        buf = tuple(islice(_xy, 0, 256))
        if not buf:
            break
        x, y = rowcol(dt, *zip(*buf))
        rv.extend(zip(x, y))
    return rv


def sort_xy(dataset, xy):
    x, y = tuple(zip(*xy))
    return np.lexsort([y, x])
    

def sample_gen(dataset, xy, indexes=None, masked=False, sorter=None):
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
    sorter : iterable|callable, default: None
        A sequence of indices that sort xy. A callable function is
        also accepted that takes two arguments (dataset, xy) and 
        returns a sequence of indices.
        Reordering xy can often yield better performance.
        This will hold all the points in memory at once and may be
        memory intensive.

        Note: The sorting function is called on the transformed
        x, y coordinates.

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
    if sorter is None:
        sample_order = range(len(samples))
    elif callable(sorter):
        sample_order = sorter(dataset, samples)
    else:
        sample_order = samples

    for i in sample_order:
        row, col = samples[i]
        if 0 <= row < height and 0 <= col < width:
            win = Window(col, row, 1, 1)
            data = read(indexes, window=win, masked=masked)
            samples[i] = data[:, 0, 0]
        else:
            samples[i] = nodata
    return iter(samples)

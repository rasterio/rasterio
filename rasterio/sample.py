# Workaround for issue #378. A pure Python generator.

from itertools import zip_longest

import numpy as np

from rasterio.enums import MaskFlags
from rasterio.windows import Window
from rasterio.transform import rowcol


def _grouper(iterable, n, fillvalue=None):
    "Collect data into non-overlapping fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    # from itertools recipes
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


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

    Yields
    ------
    array
        A array of length equal to the number of specified indexes
        containing the dataset values for the bands corresponding to
        those indexes.

    """
    dt = dataset.transform
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
        mask_flags = [set(dataset.mask_flag_enums[i - 1]) for i in indexes]
        dataset_is_masked = any(
            {MaskFlags.alpha, MaskFlags.per_dataset, MaskFlags.nodata} & enums
            for enums in mask_flags
        )
        mask = [
            False if dataset_is_masked and enums == {MaskFlags.all_valid} else True
            for enums in mask_flags
        ]
        nodata = np.ma.array(nodata, mask=mask)

    for pts in _grouper(xy, 256):
        pts = zip(*filter(lambda x: x is not None, pts))

        for row_off, col_off in zip(*rowcol(dt, *pts)):
            if row_off < 0 or col_off < 0 or row_off >= height or col_off >= width:
                yield nodata
            else:
                window = Window(col_off, row_off, 1, 1)
                data = read(indexes, window=window, masked=masked)
                yield data[:, 0, 0]

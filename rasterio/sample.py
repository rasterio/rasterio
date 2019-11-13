# Workaround for issue #378. A pure Python generator.

import numpy

from rasterio.windows import Window


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
    index = dataset.index
    read = dataset.read

    if isinstance(indexes, int):
        indexes = [indexes]

    for x, y in xy:
        row_off, col_off = index(x, y)
#        if row_off < 0 or col_off < 0:
#            yield numpy.ones((dataset.count,), dtype=dataset.dtypes[0]) * dataset.nodata
#        else:
        window = Window(col_off, row_off, 1, 1)
        data = read(indexes, window=window, masked=masked, boundless=True)
        yield data[:, 0, 0]

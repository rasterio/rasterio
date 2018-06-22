# Workaround for issue #378. A pure Python generator.

import numpy

from rasterio.windows import Window


def sample_gen(dataset, xy, indexes=None):
    """Generator for sampled pixels"""
    index = dataset.index
    read = dataset.read

    if isinstance(indexes, int):
        indexes = [indexes]

    for x, y in xy:
        row_off, col_off = index(x, y)
        if row_off < 0 or col_off < 0:
            yield numpy.ones((dataset.count,), dtype=dataset.dtypes[0]) * dataset.nodata
        else:
            window = Window(col_off, row_off, 1, 1)
            data = read(indexes, window=window, masked=False)
            yield data[:, 0, 0]

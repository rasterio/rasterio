# Workaround for issue #378. A pure Python generator.

import numpy as np

import rasterio._loading
with rasterio._loading.add_gdal_dll_directories():
    from rasterio.enums import MaskFlags
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
    height = dataset.height
    width = dataset.width

    if indexes is None:
        indexes = dataset.indexes
    elif isinstance(indexes, int):
        indexes = [indexes]

    nodata = np.full(len(indexes), (dataset.nodata or 0),  dtype=dataset.dtypes[0])
    if masked:
        # Masks for masked arrays are inverted (False means valid)
        mask = [~(MaskFlags.all_valid in dataset.mask_flag_enums[i-1]) for i in indexes]
        nodata = np.ma.array(nodata, mask=mask)

    for x, y in xy:

        row_off, col_off = index(x, y)

        if row_off < 0 or col_off < 0 or row_off >= height or col_off >= width:
            yield nodata
        else:
            window = Window(col_off, row_off, 1, 1)
            data = read(indexes, window=window, masked=masked)
            yield data[:, 0, 0]

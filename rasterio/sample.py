# Workaround for issue #378. A pure Python generator.

from rasterio.windows import Window


def sample_gen(dataset, xy, indexes=None):
    """Generator for sampled pixels"""
    index = dataset.index
    read = dataset.read

    if isinstance(indexes, int):
        indexes = [indexes]

    for x, y in xy:
        r, c = index(x, y)
        window = Window(c, r, 1, 1)
        data = read(indexes, window=window, masked=False, boundless=True)
        yield data[:, 0, 0]

# Workaround for issue #378. A pure Python generator.

def sample_gen(dataset, xy, indexes=None):
    index = dataset.index
    read = dataset.read
    for x, y in xy:
        r, c = index(x, y)
        window = ((r, r+1), (c, c+1))
        data = read(indexes, window=window, masked=False, boundless=True)
        yield data[:,0,0]

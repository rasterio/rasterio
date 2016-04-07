from pprint import pprint
import rasterio
import numpy as np

path = "tests/data/RGB.byte.tif"
with rasterio.open(path) as src:
    array = src.read()

stats = []
for band in array:
    stats.append({
        'min': band.min(),
        'mean': band.mean(),
        'median': np.median(band),
        'max': band.max()})

pprint(stats)

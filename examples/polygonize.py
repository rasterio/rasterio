import pprint

import rasterio
import rasterio._features as ftrz

with rasterio.open('box.png') as src:
    image = src.read_band(1)

pprint.pprint(
    list(ftrz.polygonize(image)))

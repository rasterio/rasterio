import pprint

import rasterio
from rasterio.features import shapes

with rasterio.open('tests/data/shade.tif') as src:
    image = src.read(1)

# Print the first two shapes...
pprint.pprint(
    list(shapes(image))[:2]
)

import rasterio
from scipy.signal import medfilt

path = "tests/data/RGB.byte.tif"
output = "/tmp/filtered.tif"

with rasterio.open(path) as src:
    array = src.read()
    profile = src.profile

# apply a 5x5 median filter to each band
filtered = medfilt(array, (1, 5, 5)).astype('uint8')

# Write to tif, using the same profile as the source
with rasterio.open(output, 'w', **profile) as dst:
    dst.write(filtered)

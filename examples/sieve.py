import numpy
import rasterio
from rasterio.features import sieve, shapes
import subprocess

with rasterio.open('rasterio/tests/data/dem.tif') as src:
    slope = src.read_band(1)

print "Slope shapes: %d" % len(list(shapes(slope)))

sieved = sieve(slope, 9)

print "Sieved (5) shapes: %d" % len(list(shapes(sieved)))

kwargs = src.meta

with rasterio.open('example-sieved.tif', 'w', **kwargs) as dst:
    dst.write_band(1, sieved)

# Dump out gdalinfo's report card and open the image.
info = subprocess.check_output(
    ['gdalinfo', '-stats', 'example-sieved.tif'])
print(info)
subprocess.call(['open', 'example-sieved.tif'])

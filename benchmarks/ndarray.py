# Benchmark for read of raster data to ndarray

import timeit

import rasterio
from osgeo import gdal

# GDAL
s = """
src = gdal.Open('rasterio/tests/data/RGB.byte.tif')
arr = src.GetRasterBand(1).ReadAsArray()
src = None
"""

n = 100

t = timeit.timeit(s, setup='from osgeo import gdal', number=n)
print("GDAL:")
print("%f msec\n" % (1000*t/n))

# Rasterio
s = """
with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
    arr = src.read_band(1)
"""

t = timeit.timeit(s, setup='import rasterio', number=n)
print("Rasterio:")
print("%f msec\n" % (1000*t/n))

# GDAL Extras
s = """
src = gdal.Open('rasterio/tests/data/RGB.byte.tif')
transform = src.GetGeoTransform()
srs = osr.SpatialReference()
srs.ImportFromWkt(src.GetProjectionRef())
wkt = srs.ExportToWkt()
proj = srs.ExportToProj4()
arr = src.GetRasterBand(1).ReadAsArray()
src = None
"""

n = 1000

t = timeit.timeit(s, setup='from osgeo import gdal; from osgeo import osr', number=n)
print("GDAL + Extras:\n")
print("%f usec\n" % (t/n))

# Rasterio
s = """
with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
    transform = src.transform
    proj = src.crs
    wkt = src.crs_wkt
    arr = src.read_band(1)
"""

t = timeit.timeit(s, setup='import rasterio', number=n)
print("Rasterio:\n")
print("%f usec\n" % (t/n))


import pstats, cProfile

s = """
with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
    arr = src.read_band(1, window=(10, 10, 10, 10))
"""

cProfile.runctx(s, globals(), locals(), "Profile.prof")

s = pstats.Stats("Profile.prof")
s.strip_dirs().sort_stats("time").print_stats()

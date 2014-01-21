import numpy
import rasterio
import subprocess

with rasterio.drivers():

    # Read raster bands directly to Numpy arrays.
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        r, g, b = map(src.read_band, (1, 2, 3))

    # Combine arrays using the 'iadd' ufunc. Expecting that the sum will
    # exceed the 8-bit integer range, initialize it as 16-bit. Adding other
    # arrays to it in-place converts those arrays up and preserves the type
    # of the total array.
    total = numpy.zeros(r.shape, dtype=rasterio.uint16)
    for band in (r, g, b):
        total += band
    total /= 3
    assert total.dtype == rasterio.uint16

    # Write the product as a raster band to a new 8-bit file. For keyword
    # arguments, we start with the meta attributes of the source file, but
    # then change the band count to 1, set the dtype to uint8, and specify
    # LZW compression.
    kwargs = src.meta
    kwargs.update(
        dtype=rasterio.uint8,
        count=1,
        compress='lzw')

    with rasterio.open('example-total.tif', 'w', **kwargs) as dst:
        dst.write_band(1, total.astype(rasterio.uint8))

# Dump out gdalinfo's report card and open the image.
info = subprocess.check_output(
    ['gdalinfo', '-stats', 'example-total.tif'])
print(info)
subprocess.call(['open', 'example-total.tif'])


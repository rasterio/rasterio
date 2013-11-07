import rasterio

# Read raster bands directly to Numpy arrays.
with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
    r = src.read_band(0).astype(rasterio.float32)
    g = src.read_band(1).astype(rasterio.float32)
    b = src.read_band(2).astype(rasterio.float32)
    
# Combine arrays using the 'add' ufunc and then convert back to btyes.
total = (r + g + b)/3.0
total = total.astype(rasterio.ubyte)

# Write the product as a raster band to a new file. For keyword arguments,
# we use meta attributes of the source file, but change the band count to 1.
with rasterio.open(
        '/tmp/total.tif', 'w',
        dtype=total.dtype,
        **dict(src.meta, **{'count':1})
        ) as dst:
    dst.write_band(0, total)

import subprocess
info = subprocess.check_output(['gdalinfo', '-stats', '/tmp/total.tif'])
print(info)


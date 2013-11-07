rasterio
========

Fast and direct raster I/O for Python programmers who use Numpy.

This package is aimed at developers who want little more than to read raster
images into Numpy arrays or buffers, operate on them in Python (or Cython), and
write the results out to new raster files.

Rasterio employs GDAL under the hood for file I/O and raster formatting.

Example
-------

Here's an example of the features rasterio aims to provide.

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

Dependencies
------------

C library dependecies:

- GDAL

Python package dependencies:

- numpy
- six
- Tests require nose

Testing
-------

From the repo directory:

    $ nosetests rasterio/tests

License
-------

See LICENSE.txt

Authors
-------

See AUTHORS.txt

Changes
-------

See CHANGES.txt


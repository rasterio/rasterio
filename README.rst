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

.. code-block:: python

    import rasterio
    import subprocess

    # Read raster bands directly to Numpy arrays.
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        r = src.read_band(0)
        g = src.read_band(1)
        b = src.read_band(2)
        assert [b.dtype.type for b in (r, g, b)] == src.dtypes
        
    # Combine arrays using the 'add' ufunc. Expecting that the sum will exceed the
    # 8-bit integer range, I convert to float32.
    r = r.astype(rasterio.float32)
    g = g.astype(rasterio.float32)
    b = b.astype(rasterio.float32)
    total = (r + g + b)/3.0

    # Write the product as a raster band to a new 8-bit file. For keyword
    # arguments, we start with the meta attributes of the source file, but then
    # change the band count to 1, set the dtype to uint8, and specify LZW
    # compression.
    with rasterio.open(
            '/tmp/total.tif', 'w',
            **dict(
                src.meta, 
                **{'dtype': rasterio.uint8, 'count':1, 'compress': 'lzw'})
            ) as dst:
        dst.write_band(0, total.astype(rasterio.uint8))

    # Dump out gdalinfo's report card.
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

From the repo directory, run nosetests.

.. code-block:: console

    $ nosetests

License
-------

See LICENSE.txt

Authors
-------

See AUTHORS.txt

Changes
-------

See CHANGES.txt


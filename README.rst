rasterio
========

Fast and direct geospatial raster I/O for Python programmers who use Numpy.

This package is aimed at developers who want little more than to read raster
images into Numpy arrays or buffers, operate on them in Python (or Cython), and
write the results out to new GeoTIFF files.

Rasterio employs GDAL under the hood for file I/O and raster formatting.

Example
-------

Here's an example of the features rasterio aims to provide. Three bands are
read from an image and summed to produce something like a panchromatic band.
This new band is then written to a single band TIFF.

.. code-block:: python

    import rasterio
    import subprocess
    
    # Read raster bands directly to Numpy arrays.
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        r = src.read_band(1)
        g = src.read_band(2)
        b = src.read_band(3)
        assert [b.dtype.type for b in (r, g, b)] == src.dtypes
    
    # Combine arrays using the 'add' ufunc. Expecting that the sum will
    # exceed the 8-bit integer range, convert to 16-bit.
    
    r = r.astype(rasterio.uint16)
    g = g.astype(rasterio.uint16)
    b = b.astype(rasterio.uint16)
    total = (r + g + b)/3
    
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

Simple access is provided to properties of a geospatial raster file.

.. code-block:: python

    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        print(src.width, src.height)
        print(src.crs)
        print(src.transform)
        print(src.count)
        print(src.indexes)

    # Output:
    # (791, 718)
    # {u'units': u'm', u'no_defs': True, u'ellps': u'WGS84', u'proj': u'utm', u'zone': 18}
    # [101985.0, 300.0379266750948, 0.0, 2826915.0, 0.0, -300.041782729805]
    # 3
    # [1, 2, 3]

Rasterio also affords conversion of GeoTIFFs, on copy, to other formats.

.. code-block:: python

    rasterio.copy(
        'example-total.tif',
        'example-total.jpg', 
        driver='JPEG')
    
    subprocess.call(['open', 'example-total.jpg'])

Dependencies
------------

C library dependecies:

- GDAL

Python package dependencies (see also requirements.txt):

- Numpy
- setuptools
- six

Development also requires (see requirements-dev.txt)

- Cython
- nose

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


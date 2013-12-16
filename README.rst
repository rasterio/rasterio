rasterio
========

Clean and fast and geospatial raster I/O for Python programmers who use Numpy.

This library is designed for developers who want to read raster datasets into
Numpy arrays or buffers, operate on them in Python (or Cython), and write the
results out to new GeoTIFF files.

Rasterio employs GDAL under the hood for file I/O and raster formatting. It
aims to let you get more done with less code and fewer bugs than you can with
other GDAL interfaces.

Example
-------

Here's an example of the basic features rasterio provides. Three bands are
read from an image and summed to produce something like a panchromatic band.
This new band is then written to a new single band TIFF.

.. code-block:: python

    import numpy
    import rasterio
    import subprocess
    
    # Read raster bands directly to Numpy arrays.
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        b, g, r = map(src.read_band, (1, 2, 3))
    
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

.. image:: http://farm6.staticflickr.com/5501/11393054644_74f54484d9_z_d.jpg
   :width: 640
   :height: 581

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

Development also requires (see requirements-dev.txt)

- Cython
- nose

Installation
------------

Rasterio is a C extension and there are not yet any binary releases. You'll
need a working compiler (XCode on OS X, etc).

.. code-block:: console

    $ pip install Numpy
    $ pip install rasterio

The Numpy headers are required to run the rasterio setup script. Numpy has to
be installed first.

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


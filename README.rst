rasterio
========

Rasterio is GDAL and Numpy-based Python library for geospatial raster data access.

.. image:: https://travis-ci.org/mapbox/rasterio.png?branch=master
   :target: https://travis-ci.org/mapbox/rasterio

Rasterio employs GDAL under the hood for file I/O and raster formatting. Its
functions typically accept and return Numpy ndarrays. Rasterio is designed to
make working with geospatial raster data more productive and more fun.

Example
-------

Here's an example of the basic features rasterio provides. Three bands are
read from an image and summed to produce something like a panchromatic band.
This new band is then written to a new single band TIFF.

.. code-block:: python

    import numpy
    import rasterio
    import subprocess
    
    # Register format drivers with a context manager
    
    with rasterio.drivers():
        
        # Read raster bands directly to Numpy arrays.
        #
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
            b, g, r = map(src.read_band, (1, 2, 3))
        
        # Combine arrays using the 'iadd' ufunc. Expecting that the sum
        # will exceed the 8-bit integer range, initialize it as 16-bit.
        # Adding other arrays to it in-place converts those arrays up
        # and preserves the type of the total array.

        total = numpy.zeros(r.shape, dtype=rasterio.uint16)
        for band in (r, g, b):
            total += band
        total /= 3
        assert total.dtype == rasterio.uint16

        # Write the product as a raster band to a new 8-bit file. For
        # keyword arguments, we start with the meta attributes of the
        # source file, but then change the band count to 1, set the
        # dtype to uint8, and specify LZW compression.

        kwargs = src.meta
        kwargs.update(
            dtype=rasterio.uint8,
            count=1,
            compress='lzw')
        
        with rasterio.open('example-total.tif', 'w', **kwargs) as dst:
            dst.write_band(1, total.astype(rasterio.uint8))

    # At the end of the ``with rasterio.drivers()`` block, context
    # manager exits and all drivers are de-registered.

    # Dump out gdalinfo's report card and open the image.
    
    info = subprocess.check_output(
        ['gdalinfo', '-stats', 'example-total.tif'])
    print(info)
    subprocess.call(['open', 'example-total.tif'])

.. image:: http://farm6.staticflickr.com/5501/11393054644_74f54484d9_z_d.jpg
   :width: 640
   :height: 581

The rasterio.drivers() function and context manager are new in 0.5. The
example above shows the way to use it to register and de-register
drivers in a deterministic and efficient way. Code written for rasterio
0.4 will continue to work: opened raster datasets may manage the global
driver registry if no other manager is present.

Simple access is provided to properties of a geospatial raster file.

.. code-block:: python
    
    with rasterio.drivers():

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
    
    with rasterio.drivers():

        rasterio.copy(
            'example-total.tif',
            'example-total.jpg', 
            driver='JPEG')
    
    subprocess.call(['open', 'example-total.jpg'])

Interactive Interpreter
-----------------------

Like a gdalinfo on steroids, pass a filename to "python -m rasterio.tool".

.. code-block:: console

    $ python -m rasterio.tool rasterio/tests/data/shade.tif
    Rasterio 0.5.1 Interactive Interpreter
    Type "src.name", "src.read_band(1)", or "help(src)" for more information.
    >>> src.name
    'rasterio/tests/data/shade.tif'
    >>> src.shape
    (1024, 1024)
    >>> import pprint
    >>> pprint.pprint(src.crs)
    {u'a': 6378137,
     u'b': 6378137,
     u'k': 1,
     u'lat_ts': 0,
     u'lon_0': 0,
     u'nadgrids': u'@null',
     u'no_defs': True,
     u'proj': u'merc',
     u'units': u'm',
     u'wktext': True,
     u'x_0': 0,
     u'y_0': 0}
    >>> b = src.read_band(1)
    >>> b
    array([[255, 255, 255, ...,   0,   0,   0],
           [255, 255, 255, ...,   0,   0,   0],
           [255, 255, 255, ...,   0,   0,   0],
           ...,
           [255, 255, 255, ..., 255, 255, 255],
           [255, 255, 255, ..., 255, 255, 255],
           [255, 255, 255, ..., 255, 255, 255]], dtype=uint8)
    >>> b.min(), b.max(), b.mean()
    (0, 255, 224.75362300872803)

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
need a working compiler (XCode on OS X, etc). To install from the source 
distribution on PyPI, do the following:

.. code-block:: console

    $ pip install -r https://raw.github.com/mapbox/rasterio/master/requirements.txt
    $ pip install rasterio>=0.5

To install from a forked repo, do this (in a virtualenv, preferably):

.. code-block:: console

    $ pip install -r requirements-dev.txt
    $ python setup.py install

The Numpy headers are required to run the rasterio setup script. Numpy has to
be installed (via the indicated requirements file) before rasterio can be
installed. See rasterio's Travis `configuration <https://github.com/mapbox/rasterio/blob/master/.travis.yml>`__ for more guidance.

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


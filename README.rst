========
Rasterio
========

Rasterio reads and writes geospatial raster datasets.

.. image:: https://travis-ci.org/mapbox/rasterio.png?branch=master
   :target: https://travis-ci.org/mapbox/rasterio

.. image:: https://coveralls.io/repos/mapbox/rasterio/badge.png
   :target: https://coveralls.io/r/mapbox/rasterio

Rasterio employs GDAL under the hood for file I/O and raster formatting. Its
functions typically accept and return Numpy ndarrays. Rasterio is designed to
make working with geospatial raster data more productive and more fun.

Rasterio is pronounced raw-STEER-ee-oh.

Example
=======

Here's a simple example of the basic features rasterio provides. Three bands
are read from an image and summed to produce something like a panchromatic
band.  This new band is then written to a new single band TIFF. 

.. code-block:: python

    import numpy
    import rasterio
    import subprocess
    
    # Register GDAL format drivers and configuration options with a
    # context manager.
    
    with rasterio.drivers(CPL_DEBUG=True):
        
        # Read raster bands directly to Numpy arrays.
        #
        with rasterio.open('tests/data/RGB.byte.tif') as src:
            b, g, r = src.read()
        
        # Combine arrays in place. Expecting that the sum will 
        # temporarily exceed the 8-bit integer range, initialize it as
        # 16-bit. Adding other arrays to it in-place converts those
        # arrays "up" and preserves the type of the total array.

        total = numpy.zeros(r.shape, dtype=rasterio.uint16)
        for band in r, g, b:
            total += band
        total /= 3

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

The rasterio.drivers() function and context manager are new in 0.5. The example
above shows the way to use it to register and de-register drivers in
a deterministic and efficient way. Code written for rasterio 0.4 will continue
to work: opened raster datasets may manage the global driver registry if no
other manager is present.

API Overview
============

Simple access is provided to properties of a geospatial raster file.

.. code-block:: python
    
    with rasterio.drivers():

        with rasterio.open('tests/data/RGB.byte.tif') as src:
            print(src.width, src.height)
            print(src.crs)
            print(src.affine)
            print(src.count)
            print(src.indexes)

    # Output:
    # (791, 718)
    # {u'units': u'm', u'no_defs': True, u'ellps': u'WGS84', u'proj': u'utm', u'zone': 18}
    # Affine(300.0379266750948, 0.0, 101985.0,
    #        0.0, -300.041782729805, 2826915.0)
    # 3
    # [1, 2, 3]

Rasterio also affords conversion of GeoTIFFs to other formats.

.. code-block:: python
    
    with rasterio.drivers():

        rasterio.copy(
            'example-total.tif',
            'example-total.jpg', 
            driver='JPEG')
    
    subprocess.call(['open', 'example-total.jpg'])

Rasterio CLI
============

Rasterio's command line interface, named "rio", is documented at `cli.rst
<https://github.com/mapbox/rasterio/blob/master/docs/cli.rst>`__. Its ``rio
insp`` command opens the hood of any raster dataset so you can poke around
using Python.

.. code-block:: pycon

    $ rio insp tests/data/RGB.byte.tif
    Rasterio 0.10 Interactive Inspector (Python 3.4.1)
    Type "src.meta", "src.read_band(1)", or "help(src)" for more information.
    >>> src.name
    'tests/data/RGB.byte.tif'
    >>> src.closed
    False
    >>> src.shape
    (718, 791)
    >>> src.crs
    {'init': 'epsg:32618'}
    >>> b, g, r = src.read()
    >>> b
    masked_array(data =
     [[-- -- -- ..., -- -- --]
     [-- -- -- ..., -- -- --]
     [-- -- -- ..., -- -- --]
     ...,
     [-- -- -- ..., -- -- --]
     [-- -- -- ..., -- -- --]
     [-- -- -- ..., -- -- --]],
                 mask =
     [[ True  True  True ...,  True  True  True]
     [ True  True  True ...,  True  True  True]
     [ True  True  True ...,  True  True  True]
     ...,
     [ True  True  True ...,  True  True  True]
     [ True  True  True ...,  True  True  True]
     [ True  True  True ...,  True  True  True]],
           fill_value = 0)

    >>> b.min(), b.max(), b.mean()
    (1, 255, 44.434478650699106)

Installation
============

Dependencies
------------

Rasterio has one C library dependency: GDAL >=1.9. GDAL itself depends on a
number of other libraries provided by most major operating systems and also
depends on the non standard GEOS and PROJ4 libraries.

Python package dependencies (see also requirements.txt): affine, cligj (and
click), enum34, numpy.

Development also requires (see requirements-dev.txt) Cython and other packages.

Installing from binaries
---------------------------------------

OS X
----

Binary wheels with the GDAL, GEOS, and PROJ4 libraries included are available
for OS X versions 10.7+ starting with Rasterio version 0.17. To install, just
run ``pip install rasterio``. These binary wheels are preferred by newer
versions of pip. If you don't want these wheels and want to install from
a source distribution, run ``pip install rasterio --no-use-wheel`` instead.

The included GDAL library is fairly minimal, providing only the format drivers
that ship with GDAL and are enabled by default. To get access to more formats,
you must build from a source distribution (see below).

Binary wheels for other operating systems will be available in a future
release.

Windows
-------

Binary wheels for rasterio and GDAL are created by Christoph Gohlke and are available `here
<http://www.lfd.uci.edu/~gohlke/pythonlibs/#rasterio>`__.

To install rasterio, simply download both binaries for your system and run something like this:

.. code-block:: console

    $ pip install wheel
    $ install GDAL-1.11.2-cp27-none-win32.whl
    $ install rasterio-0.24.0-cp27-none-win32.whl

Installing from the source distribution
---------------------------------------

Rasterio is a Python C extension and to build you'll need a working compiler
(XCode on OS X etc). You'll also need Numpy preinstalled; the Numpy headers are
required to run the rasterio setup script. Numpy has to be installed (via the
indicated requirements file) before rasterio can be installed. See rasterio's
Travis `configuration
<https://github.com/mapbox/rasterio/blob/master/.travis.yml>`__ for more
guidance.

Linux
-----

The following commands are adapted from Rasterio's Travis-CI configuration.

.. code-block:: console

    $ sudo add-apt-repository ppa:ubuntugis/ppa
    $ sudo apt-get update
    $ sudo apt-get install python-numpy libgdal1h gdal-bin libgdal-dev
    $ pip install rasterio

Adapt them as necessary for your Linux system.

OS X
----

For a Homebrew based Python environment, do the following.

.. code-block:: console

    $ brew install gdal
    $ pip install rasterio

Windows
-------

You can download a binary distribution of GDAL from `here
<http://www.gisinternals.com/release.php>`__.  You will also need to download
the compiled libraries and headers (include files).

When building from source on Windows, it is important to know that setup.py
cannot rely on gdal-config, which is only present on UNIX systems, to discover
the locations of header files and libraries that rasterio needs to compile its
C extensions. On Windows, these paths need to be provided by the user. You
will need to find the include files and the library files for gdal and use
setup.py as follows.

.. code-block:: console

    $ python setup.py build_ext -I<path to gdal include files> -lgdal_i -L<path to gdal library>
    $ python setup.py install

We have had success compiling code using the same version of Microsoft's
Visual Studio used to compile the targeted version of Python (more info on
versions used `here
<https://docs.python.org/devguide/setup.html#windows>`__.).

Note: The GDAL dll (gdal111.dll) and gdal-data directory need to be in your
Windows PATH otherwise rasterio will fail to work.

Testing
-------

From the repo directory, run py.test

.. code-block:: console

    $ py.test


Note: some tests do not succeed on Windows (see
`#66
<https://github.com/mapbox/rasterio/issues/66>`__.).


Documentation
-------------

See https://github.com/mapbox/rasterio/tree/master/docs.

License
-------

See LICENSE.txt

Authors
-------

See AUTHORS.txt

Changes
-------

See CHANGES.txt

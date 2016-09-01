========
Rasterio
========

Rasterio reads and writes geospatial raster data.

.. image:: https://travis-ci.org/mapbox/rasterio.png?branch=master
   :target: https://travis-ci.org/mapbox/rasterio

.. image:: https://coveralls.io/repos/github/mapbox/rasterio/badge.svg?branch=master
   :target: https://coveralls.io/github/mapbox/rasterio?branch=master

Geographic information systems use GeoTIFF and other formats to organize and
store gridded, or raster, datasets. Rasterio reads and writes these formats and
provides a Python API based on N-D arrays.

Rasterio supports Python 2.7 and 3.3-3.5 on Linux and Mac OS X.

Read the documentation for more details: https://mapbox.github.io/rasterio/.

Example
=======

Here's an example of some basic features that Rasterio provides. Three bands
are read from an image and averaged to produce something like a panchromatic
band.  This new band is then written to a new single band TIFF.

.. code-block:: python

    import numpy as np
    import rasterio

    # Read raster bands directly to Numpy arrays.
    #
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        r, g, b = src.read()

    # Combine arrays in place. Expecting that the sum will
    # temporarily exceed the 8-bit integer range, initialize it as
    # a 64-bit float (the numpy default) array. Adding other
    # arrays to it in-place converts those arrays "up" and
    # preserves the type of the total array.
    total = np.zeros(r.shape)
    for band in r, g, b:
        total += band
    total /= 3

    # Write the product as a raster band to a new 8-bit file. For
    # the new file's profile, we start with the meta attributes of
    # the source file, but then change the band count to 1, set the
    # dtype to uint8, and specify LZW compression.
    profile = src.profile
    profile.update(dtype=rasterio.uint8, count=1, compress='lzw')

    with rasterio.open('example-total.tif', 'w', **profile) as dst:
        dst.write(total.astype(rasterio.uint8), 1)

The output:

.. image:: http://farm6.staticflickr.com/5501/11393054644_74f54484d9_z_d.jpg
   :width: 640
   :height: 581

API Overview
============

Rasterio gives access to properties of a geospatial raster file.

.. code-block:: python

    with rasterio.open('tests/data/RGB.byte.tif') as src:
        print(src.width, src.height)
        print(src.crs)
        print(src.transform)
        print(src.count)
        print(src.indexes)

    # Printed:
    # (791, 718)
    # {u'units': u'm', u'no_defs': True, u'ellps': u'WGS84', u'proj': u'utm', u'zone': 18}
    # Affine(300.0379266750948, 0.0, 101985.0,
    #        0.0, -300.041782729805, 2826915.0)
    # 3
    # [1, 2, 3]

A rasterio dataset also provides methods for getting extended array slices given
georeferenced coordinates.


.. code-block:: python

    with rasterio.open('tests/data/RGB.byte.tif') as src:
        print src.window(**src.window_bounds(((100, 200), (100, 200))))

    # Printed:
    # ((100, 200), (100, 200))

Rasterio CLI
============

Rasterio's command line interface, named "rio", is documented at `cli.rst
<https://github.com/mapbox/rasterio/blob/master/docs/cli.rst>`__. Its ``rio
insp`` command opens the hood of any raster dataset so you can poke around
using Python.

.. code-block:: pycon

    $ rio insp tests/data/RGB.byte.tif
    Rasterio 0.10 Interactive Inspector (Python 3.4.1)
    Type "src.meta", "src.read(1)", or "help(src)" for more information.
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

Rio Plugins
-----------

Rio provides the ability to create subcommands using plugins.  See
`cli.rst <https://github.com/mapbox/rasterio/blob/master/docs/cli.rst#rio-plugins>`__
for more information on building plugins.

See the
`plugin registry <https://github.com/mapbox/rasterio/wiki/Rio-plugin-registry>`__
for a list of available plugins.


Installation
============

Please install Rasterio in a `virtual environment
<https://www.python.org/dev/peps/pep-0405/>`__ so that its requirements don't
tamper with your system's Python.

Dependencies
------------

Rasterio has a C library dependency: GDAL >=1.9. GDAL itself depends on some other libraries provided by most major operating systems and also
depends on the non standard GEOS and PROJ4 libraries. How to meet these
requirement will be explained below.

Rasterio's Python dependencies are listed in its requirements.txt file.

Development also requires (see requirements-dev.txt) Cython and other packages.

Binary Distributions
--------------------

Use a binary distributions that directly or indirectly provide GDAL if
possible.

Linux
+++++

Rasterio distributions are available from UbuntuGIS and Anaconda's conda-forge
channel.

`Manylinux1 <https://github.com/pypa/manylinux>`__ distributions may be
available in the future.

OS X
++++

Binary distributions with GDAL, GEOS, and PROJ4 libraries included are available
for OS X versions 10.7+ starting with Rasterio version 0.17. To install,
run ``pip install rasterio``. These binary wheels are preferred by newer
versions of pip.

If you don't want these wheels and want to install from a source distribution,
run ``pip install rasterio --no-binary rasterio`` instead.

The included GDAL library is fairly minimal, providing only the format drivers
that ship with GDAL and are enabled by default. To get access to more formats,
you must build from a source distribution (see below).

Windows
+++++++

Binary wheels for rasterio and GDAL are created by Christoph Gohlke and are
available from his website.

To install rasterio, simply download both binaries for your system (`rasterio
<http://www.lfd.uci.edu/~gohlke/pythonlibs/#rasterio>`__ and `GDAL
<http://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal>`__) and run something like
this from the downloads folder:

.. code-block:: console

    $ pip install -U pip
    $ pip install GDAL-2.0.2-cp27-none-win32.whl
    $ pip install rasterio-0.34.0-cp27-cp27m-win32.whl

Source Distributions
--------------------

Rasterio is a Python C extension and to build you'll need a working compiler
(XCode on OS X etc). You'll also need Numpy preinstalled; the Numpy headers are
required to run the rasterio setup script. Numpy has to be installed (via the
indicated requirements file) before rasterio can be installed. See rasterio's
Travis `configuration
<https://github.com/mapbox/rasterio/blob/master/.travis.yml>`__ for more
guidance.

Linux
+++++

The following commands are adapted from Rasterio's Travis-CI configuration.

.. code-block:: console

    $ sudo add-apt-repository ppa:ubuntugis/ppa
    $ sudo apt-get update
    $ sudo apt-get install gdal-bin libgdal-dev
    $ pip install -U pip
    $ pip install rasterio

Adapt them as necessary for your Linux system.

OS X
++++

For a Homebrew based Python environment, do the following.

.. code-block:: console

    $ brew upgrade
    $ brew install gdal
    $ pip install -U pip
    $ pip install --no-use-wheel rasterio

Alternatively, you can install GDAL binaries from `kyngchaos
<http://www.kyngchaos.com/software/frameworks#gdal_complete>`__.  You will then
need to add the installed location ``/Library/Frameworks/GDAL.framework/Programs``
to your system path.

Windows
+++++++

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

Development and Testing
-----------------------

See `CONTRIBUTING.rst <CONTRIBUTING.rst/>`__.

Documentation
-------------

See `docs/ <docs/>`__.

License
-------

See `LICENSE.txt <LICENSE.txt>`__.

Authors
-------

See `AUTHORS.txt <AUTHORS.txt>`__.

Changes
-------

See `CHANGES.txt <CHANGES.txt>`__.

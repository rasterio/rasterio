========
Rasterio
========

Rasterio reads and writes geospatial raster data.

.. image:: https://app.travis-ci.com/rasterio/rasterio.svg?branch=master
   :target: https://app.travis-ci.com/rasterio/rasterio

.. image:: https://coveralls.io/repos/github/mapbox/rasterio/badge.svg?branch=master
   :target: https://coveralls.io/github/mapbox/rasterio?branch=master
   
.. image:: https://img.shields.io/pypi/v/rasterio
   :target: https://pypi.org/project/rasterio/

Geographic information systems use GeoTIFF and other formats to organize and
store gridded, or raster, datasets. Rasterio reads and writes these formats and
provides a Python API based on N-D arrays.

Rasterio 1.3 works with Python versions 3.8 through 3.10, Numpy versions 1.18
and newer, and GDAL versions 3.1 through 3.4. Official binary packages for
Linux and Mac OS X with most built-in format drivers plus HDF5, netCDF, and
OpenJPEG2000 are available on PyPI. Unofficial binary packages for Windows are
available through other channels.

Read the documentation for more details: https://rasterio.readthedocs.io/.

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

A rasterio dataset also provides methods for getting read/write windows (like
extended array slices) given georeferenced coordinates.

.. code-block:: python

    with rasterio.open('tests/data/RGB.byte.tif') as src:
        window = src.window(*src.bounds)
        print(window)
        print(src.read(window=window).shape)

    # Printed:
    # Window(col_off=0.0, row_off=0.0, width=791.0000000000002, height=718.0)
    # (3, 718, 791)

Rasterio CLI
============

Rasterio's command line interface, named "rio", is documented at `cli.rst
<https://github.com/rasterio/rasterio/blob/master/docs/cli.rst>`__. Its ``rio
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

    >>> np.nanmin(b), np.nanmax(b), np.nanmean(b)
    (0, 255, 29.94772668847656)

Rio Plugins
-----------

Rio provides the ability to create subcommands using plugins.  See
`cli.rst <https://github.com/rasterio/rasterio/blob/master/docs/cli.rst#rio-plugins>`__
for more information on building plugins.

See the
`plugin registry <https://github.com/rasterio/rasterio/wiki/Rio-plugin-registry>`__
for a list of available plugins.


Installation
============

Please install Rasterio in a `virtual environment
<https://www.python.org/dev/peps/pep-0405/>`__ so that its requirements don't
tamper with your system's Python.

SSL certs
---------

The Linux wheels on PyPI are built on CentOS and libcurl expects certs to be in
/etc/pki/tls/certs/ca-bundle.crt. Ubuntu's certs, for example, are in
a different location. You may need to use the CURL_CA_BUNDLE environment
variable to specify the location of SSL certs on your computer. On an Ubuntu
system set the variable as shown below.

.. code-block:: console

    $ export CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt


Dependencies
------------

Rasterio has a C library dependency: GDAL >= 2.3. GDAL itself depends on some
other libraries provided by most major operating systems and also depends on
the non standard GEOS and PROJ4 libraries. How to meet these requirement will
be explained below.

Rasterio's Python dependencies are (see the package metadata file):

.. code-block:: none

    affine
    attrs
    certifi
    click>=4.0
    cligj>=0.5
    numpy
    snuggs>=1.4.1
    click-plugins
    setuptools

    [all]
    hypothesis
    pytest-cov>=2.2.0
    matplotlib
    boto3>=1.3.1
    numpydoc
    pytest>=2.8.2
    shapely
    ipython>=2.0
    sphinx
    packaging
    ghp-import
    sphinx-rtd-theme

    [docs]
    ghp-import
    numpydoc
    sphinx
    sphinx-rtd-theme

    [ipython]
    ipython>=2.0

    [plot]
    matplotlib

    [s3]
    boto3>=1.3.1

    [test]
    boto3>=1.3.1
    hypothesis
    packaging
    pytest-cov>=2.2.0
    pytest>=2.8.2
    shapely

Development requires Cython and other packages.

Binary Distributions
--------------------

Use a binary distribution that directly or indirectly provides GDAL if
possible.

The rasterio wheels on PyPI include GDAL and its own dependencies.

========  ====
Rasterio  GDAL
========  ====
1.2.3     3.2.2
1.2.4+    3.3.0
========  ====

Linux
+++++

Rasterio distributions are available from UbuntuGIS and Anaconda's conda-forge
channel.

`Manylinux1 <https://github.com/pypa/manylinux>`__ wheels are available on PyPI.

OS X
++++

Binary distributions with GDAL, GEOS, and PROJ4 libraries included are
available for OS X versions 10.9+. To install, run ``pip install rasterio``.
These binary wheels are preferred by newer versions of pip.

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
this from the downloads folder, adjusting for your Python version.

.. code-block:: console

    $ pip install -U pip
    $ pip install GDAL-3.1.4-cp39-cp39‑win_amd64.whl
    $ pip install rasterio‑1.1.8-cp39-cp39-win_amd64.whl

You can also install rasterio with conda using Anaconda's conda-forge channel.

.. code-block:: console

    $ conda install -c conda-forge rasterio


Source Distributions
--------------------

Rasterio is a Python C extension and to build you'll need a working compiler
(XCode on OS X etc). You'll also need Numpy preinstalled; the Numpy headers are
required to run the rasterio setup script. Numpy has to be installed (via the
indicated requirements file) before rasterio can be installed. See rasterio's
Travis `configuration
<https://github.com/rasterio/rasterio/blob/master/.travis.yml>`__ for more
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

    $ brew update
    $ brew install gdal
    $ pip install -U pip
    $ pip install --no-binary rasterio

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
setup.py as follows. You will also need to specify the installed gdal version
through the GDAL_VERSION environment variable.

.. code-block:: console

    $ python setup.py build_ext -I<path to gdal include files> -lgdal_i -L<path to gdal library> install

With pip

.. code-block:: console

    $ pip install --no-use-pep517 --global-option -I<path to gdal include files> -lgdal_i -L<path to gdal library> .

Note: :code:`--no-use-pep517` is required as pip currently hasn't implemented a
way for optional arguments to be passed to the build backend when using PEP 517.
See `here <https://github.com/pypa/pip/issues/5771>`__ for more details.

Alternatively environment variables (e.g. INCLUDE and LINK) used by MSVC compiler can be used to point
to include directories and library files.

We have had success compiling code using the same version of Microsoft's
Visual Studio used to compile the targeted version of Python (more info on
versions used `here
<https://docs.python.org/devguide/setup.html#windows>`__.).

Note: The GDAL DLL and gdal-data directory need to be in your
Windows PATH otherwise rasterio will fail to work.


Support
=======

The primary forum for questions about installation and usage of Rasterio is
https://rasterio.groups.io/g/main. The authors and other users will answer
questions when they have expertise to share and time to explain. Please take
the time to craft a clear question and be patient about responses.

Please do not bring these questions to Rasterio's issue tracker, which we want
to reserve for bug reports and other actionable issues.

Development and Testing
=======================

See `CONTRIBUTING.rst <CONTRIBUTING.rst/>`__.

Documentation
=============

See `docs/ <docs/>`__.

License
=======

See `LICENSE.txt <LICENSE.txt>`__.

Authors
=======

The `rasterio` project was begun at Mapbox and was transferred to the `rasterio` Github organization in October 2021.

See `AUTHORS.txt <AUTHORS.txt>`__.

Changes
=======

See `CHANGES.txt <CHANGES.txt>`__.

Who is Using Rasterio?
======================

See `here <https://libraries.io/pypi/rasterio/usage>`__.

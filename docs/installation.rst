Installation
============

Dependencies
------------

Rasterio has one C library dependency: ``GDAL >=1.11``. GDAL itself depends on
many of other libraries provided by most major operating systems and also
depends on the non standard GEOS and PROJ4 libraries.

Python package dependencies (see also requirements.txt): ``affine, cligj,
click, enum34, numpy``.

Development also requires (see requirements-dev.txt) Cython and other packages.

Installing from binaries
------------------------

OS X
****

Binary wheels with the GDAL, GEOS, and PROJ4 libraries included are available
for OS X versions 10.7+ starting with Rasterio version 0.17. To install, 
run ``pip install rasterio``. These binary wheels are preferred by newer
versions of pip. If you don't want these wheels and want to install from
a source distribution, run ``pip install rasterio --no-binary`` instead.

The included GDAL library is fairly minimal, providing only the format drivers
that ship with GDAL and are enabled by default. To get access to more formats,
you must build from a source distribution (see below).

Binary wheels for other operating systems will be available in a future
release.

Windows
*******

Binary wheels for rasterio and GDAL are created by Christoph Gohlke and are
available from his website.

To install rasterio, download both binaries for your system (`rasterio
<http://www.lfd.uci.edu/~gohlke/pythonlibs/#rasterio>`__ and `GDAL
<http://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal>`__) and run something like
this from the downloads folder:

.. code-block:: console

    $ pip install -U pip 
    $ pip install GDAL-1.11.2-cp27-none-win32.whl
    $ pip install rasterio-0.24.0-cp27-none-win32.whl


Installing with Anaconda
-------------------------

To install rasterio on the Anaconda Python distribution, please visit the
`rasterio conda-forge`_ page for install instructions. This build is maintained
separately from the rasterio distribution on PyPi and packaging issues should
be addressed on the `rasterio conda-forge`_ issue tracker. 

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
*****

The following commands are adapted from Rasterio's Travis-CI configuration.

.. code-block:: console

    $ sudo add-apt-repository ppa:ubuntugis/ppa
    $ sudo apt-get update
    $ sudo apt-get install python-numpy gdal-bin libgdal-dev
    $ pip install rasterio

Adapt them as necessary for your Linux system.

OS X
****

For a Homebrew based Python environment, do the following.

.. code-block:: console

    $ brew install gdal
    $ pip install rasterio

Windows
*******

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

.. _rasterio conda-forge: https://github.com/conda-forge/rasterio-feedstock

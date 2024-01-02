============
Installation
============

Installation of the Rasterio package is complicated by its dependency on libgdal
and other C libraries. There are easy installations paths and an advanced
installation path.

Easy installation
=================

Rasterio has several `extension modules
<https://docs.python.org/3/extending/extending.html>`__ which link against
libgdal. This complicates installation. Binary distributions (wheels)
containing libgdal and its own dependencies are available from the Python
Package Index and can be installed using pip.

.. code-block:: console

    pip install rasterio

These wheels are mainly intended to make installation easy for simple
applications, not so much for production. They are not tested for compatibility
with all other binary wheels, conda packages, or QGIS, and omit many of GDAL's
optional format drivers.

Many users find Anaconda and conda-forge a good way to install Rasterio and get
access to more optional format drivers (like TileDB and others).

Rasterio 1.4 requires Python 3.9 or higher and GDAL 3.3 or higher.

Advanced installation
=====================

Once GDAL and its dependencies are installed on your computer (how to do this
is documented at https://gdal.org) Rasterio can be built and installed using
setuptools or pip. If your GDAL installation provides the ``gdal-config``
program, the process is simpler.

Without pip:

.. code-block:: console

    GDAL_CONFIG=/path/to/gdal-config python setup.py install

With pip (version >= 22.3 is required):

.. code-block:: console

    python -m pip install --user -U pip
    GDAL_CONFIG=/path/to/gdal-config python -m pip install --user --no-binary rasterio rasterio

These are pretty much equivalent. Pip will use setuptools as the build backend.
If the gdal-config program is on your executable path, then you don't need to
set the environment variable.

Without gdal-config you will need to configure header and library locations for
the build in another way. One way to do this is to create a setup.cfg file in
the source directory with content like this:

.. code-block:: ini

    [build_ext]
    include_dirs = C:/vcpkg/installed/x64-windows/include
    libraries = gdal
    library_dirs = C:/vcpkg/installed/x64-windows/lib

This is the approach taken by Rasterio's `wheel-building workflow
<https://github.com/rasterio/rasterio-wheels/blob/main/.github/workflows/win-wheels.yaml#L67-L74>`__.
With this file in place you can run either ``python setup.py install`` or ``python -m pip install --user .``.

You can also pass those three values on the command line following the
`setuptools documentation
<https://setuptools.pypa.io/en/latest/userguide/ext_modules.html#compiler-and-linker-options>`__.
However, the setup.cfg approach is easier.

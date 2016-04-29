GDAL Option Configuration
=========================

.. todo::

    Why to use Env() instead of drivers().

    When to use with rasterio.Env() instead of a bare rasterio.open()


GDAL format drivers and some parts of the library are configurable.

From https://trac.osgeo.org/gdal/wiki/ConfigOptions:

    ConfigOptions are normally used to alter the default behavior of GDAL
    and OGR drivers and in some cases the GDAL and OGR core. They are
    essentially global variables the user can set.

GDAL Example
------------

The following is from `GDAL's test suite <https://github.com/OSGeo/gdal/blob/0b75aa3c39e6d126439fb17eed939de39f6f3720/autotest/gcore/tiff_read.py#L117-L119>`__.

.. code-block:: python

    gdal.SetConfigOption('GTIFF_FORCE_RGBA', 'YES')
    ds = gdal.Open('data/stefan_full_greyalpha.tif')
    gdal.SetConfigOption('GTIFF_FORCE_RGBA', None)

With GDAL's C or Python API, you call a function once to set a global
configuration option before you need it and once again after you're through
to unset it.

Downsides of this style of configuration include:

- Options can be configured far from the code they affect.
- There is no API for finding what options are currently set.
- If ``gdal.Open()`` raises an exception in the code above, the
  ``GTIFF_FORCE_RGBA`` option will not be unset.

That code example can be generalized to multiple options and made to
recover better from errors.

.. code-block:: python

    options = {'GTIFF_FORCE_RGBA': 'YES'}
    for key, val in options.items():
        gdal.SetConfigOption(key, val)
    try:
        ds = gdal.Open('data/stefan_full_greyalpha.tif')
    finally:
        for key, val in options.items():
            gdal.SetConfigOption(key, None)

This is better, but has a lot of boilerplate. Rasterio uses elements of Python
syntax, keyword arguments and the ``with`` statement, to make this cleaner
and easier to use.

Rasterio
--------

.. code-block:: python

    with rasterio.Env(GTIFF_FORCE_RGBA=True, CPL_DEBUG=True):
        with rasterio.open('data/stefan_full_greyalpha.tif') as ds:
           # Suite of code accessing dataset ``ds`` follows...

Configuration options are defined for a very specific suite of code and are
cleared when the suite exits, even if an exception is raised. The object
returned when you call ``rasterio.Env()`` handles the GDAL configuration for
you and if you want to know what options are configured at any time, you
could bind it to a name like so.

.. code-block:: python

    with rasterio.Env(GTIFF_FORCE_RGBA=True, CPL_DEBUG=True) as env:
        for key, val in env.options.items():
            print(key, val)

    # Prints:
    # ('GTIFF_FORCE_RGBA', True)
    # ('CPL_DEBUG', True)


GDAL Option Configuration
=========================

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
syntax, keyword arguments and the |WITHST|_ statement, to make this cleaner
and easier to use.

Rasterio
--------

.. code-block:: python

    with rasterio.Env(GTIFF_FORCE_RGBA=True, CPL_DEBUG=True):
        with rasterio.open('data/stefan_full_greyalpha.tif') as dataset:
           # Suite of code accessing dataset ``ds`` follows...

The object returned when you call ``rasterio.Env()`` is a context manager.  It
handles the GDAL configuration for a specific block of code and resets the
configuration when the block exits for any reason, success or failure. The
Rasterio ``with rasterio.Env()`` pattern organizes GDAL configuration into single
statements and makes its relationship to a block of code clear.

If you want to know what options are configured at any time, you could bind it
to a name like so.

.. code-block:: python

    with rasterio.Env(GTIFF_FORCE_RGBA=True, CPL_DEBUG=True) as env:
        for key, val in env.options.items():
            print(key, val)

    # Prints:
    # ('GTIFF_FORCE_RGBA', True)
    # ('CPL_DEBUG', True)

When to use rasterio.Env()
--------------------------

Rasterio code is often without the use of an ``Env`` context block. For instance,
you could use ``rasterio.open()`` directly without explicity creating an ``Env``.
In that case, the ``open`` function will initialize a default environment in
which to execute the code. Often this default environment is sufficient for most
use cases and you only need to create an explicit ``Env`` if you are customizing
the default GDAL or format options.


.. |WITHST| replace:: ``with``
.. _WITHST: https://docs.python.org/3.7/reference/compound_stmts.html#the-with-statement

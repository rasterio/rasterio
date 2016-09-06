=====================================
Switching from GDAL's Python bindings
=====================================

Switching from GDAL's Python bindings to Rasterio for new projects or new
iterations on existing projects may not be complicated. This document explains
the key similarities and differences between these two Python packages and
provides some guidelines for why and how to switch.

Mutual Incompatibility
======================

GDAL's Python module, meaning the ``gdal`` module in the ``osgeo`` namespace,
and Rasterio are mutually incompatible and should not be imported and used in
a single Python program. The reason is that they take different, naive,
incompatible approaches to managing global variables in the dynamic library
that they would share. It is assumed in multiple places in ``gdal``, such as
testing whether the count of currently registered format drivers is 0 to
determine whether any drivers need to be registered, that no other Python
module functions are modifying the variables in the dynamic library. Rasterio
makes the same kind of assumptions and consequently the state of the global
GDAL driver manager may be unpredictable. Additionally, ``gdal`` and Rasterio
register conflicting error handlers and thus the propagation of exceptions and
warnings may depend on which module was imported last.

Beyond the issues above, the modules have different styles and don't complement
each other well. The bottom line: choose ``import osgeo.gdal`` or ``import
rasterio``.

The GDAL Environment
====================

GDAL library functions are excuted in a context of format drivers, error
handlers, and format-specific configuration options that this document will
call the "GDAL Environment." With ``gdal``, this context is initialized upon
import of the module. This makes sense because ``gdal`` objects are thin
wrappers around functions and classes in the GDAL dynamic library that
generally require registration of drivers and error handlers.  The ``gdal``
module doesn't have an abstraction for the environment, but it can be modified
using functions like ``gdal.SetErrorHandler()`` and ``gdal.UseExceptions()``.

Rasterio has modules that don't require complete initialization and
configuration of GDAL (``rasterio.dtypes``, ``rasterio.profiles``, and
``rasterio.windows``, for example) and in the interest of reducing overhead
doesn't register format drivers and error handlers until they are needed. The
functions that do need fully initialized GDAL environments will ensure that
they exist. ``rasterio.open()`` is the foremost of this category of functions.
Consider the example code below.

.. code-block:: python

   import rasterio
   # The GDAL environment has no registered format drivers or error
   # handlers at this point.

   with rasterio.open('example.tif') as src:
       # Format drivers and error handlers are registered just before
       # open() executes.

Importing ``rasterio`` does not initialize the GDAL environment. Calling
``rasterio.open()`` does. This is different from ``gdal`` where ``import
osgeo.gdal``, not ``osgeo.gdal.Open()``, initializes the GDAL environment.

Rasterio has an abstraction for the GDAL environment, ``rasterio.Env``, that
can be invoked explicitly for more control over the configuration of GDAL as
shown below.

.. code-block:: python

   import rasterio
   # The GDAL environment has no registered format drivers or error
   # handlers at this point.

   with rasterio.Env(CPL_DEBUG=True, GDAL_CACHEMAX=512):
       # This ensures that all drivers are registered in the global
       # context. Within this block *only* GDAL's debugging messages
       # are turned on and the raster block cache size is set to 512MB.
   
       with rasterio.open('example.tif') as src:
           # Perform GDAL operations in this context.
           # ...
           # Done.

   # At this point, configuration options are set back to their
   # previous (possibly unset) values. The raster block cache size
   # is returned to its default (5% of available RAM) and debugging
   # messages are disabled.

As mentioned previously, ``gdal`` has no such abstraction for the GDAL
environment. The nearest approximation would be something like the code
below.

.. code-block:: python

   from osgeo import gdal

   # Define a new configuration, save the previous configuration,
   # and then apply the new one.
   new_config = {
       'CPL_DEBUG': 'ON', 'GDAL_CACHEMAX': '512'}
   prev_config = {
       key: gdal.GetConfigOption(key) for key in new_config.keys()}
   for key, val in new_config.items():
       gdal.SetConfigOption(key, val)

   # Perform GDAL operations in this context.
   # ...
   # Done.

   # Restore previous configuration.
   for key, val in prev_config.items():
       gdal.SetConfigOption(key, val)

Rasterio provides this with a single Python statement.

Reading
=======

We'll start with a raster dataset to work with, our trusty test fixture

.. code-block:: python

    >>> raster = "tests/data/RGB.byte.tif"

.. image:: /img/rgb.jpg

The most basic operation is reading the raster into a numpy array

.. code-block:: python

    >>> # osgeo.gdal
    >>> from osgeo import gdal
    >>> from osgeo.gdalconst import GA_ReadOnly
    >>> g_ds = gdal.Open(raster, GA_ReadOnly)
    >>> if not g_ds:
    ...     raise IOError("Cannot open %r as GDAL raster" % raster)
    >>> g_arr = g_ds.ReadAsArray()

The similar operation in rasterio

.. code-block:: python

    >>> # rasterio
    >>> import rasterio
    >>> with rasterio.open(raster, 'r') as src:
    ...     r_arr = src.read()


The result is the same 3D ``numpy.ndarray``

.. code-block:: python

    >>> import numpy as np
    >>> r_arr.shape
    (3, 718, 791)
    >>> assert np.array_equal(g_arr, r_arr)

If we want to grab a subset of the raster, say from row 300 to 400 and column 200 to 400.
In gdal you would express this in terms of the offset (200, 300) and size (200, 100)

.. code-block:: python

    >>> # osgeo.gdal
    >>> g_arr2 = g_ds.ReadAsArray(200, 300, 200, 100)
    >>> g_arr2.shape
    (3, 100, 200)


In Rasterio, we use a windows tuple which explicitly defines the start/stop row and columns


.. code-block:: python

    >>> # rasterio
    >>> with rasterio.open(raster, 'r') as src:
    ...     r_arr2 = src.read(window=((300, 400), (200, 400)))
    >>> assert np.array_equal(r_arr2, g_arr2)


Reading a single band into a 2D array follows a different pattern. In gdal, you get a
reference to a ``RasterBand`` and use its ``ReadAsArray`` method

.. code-block:: python

    >>> # osgeo.gdal
    >>> g_band1 = g_ds.GetRasterBand(1)
    >>> g_band1_arr = g_band1.ReadAsArray()
    >>> g_band1_arr.shape
    (718, 791)

With Rasterio, you pass the raster band index to the ``read()`` method. Note that
both Rasterio and gdal use a 1-based index to defined bands

.. code-block:: python

    >>> # rasterio
    >>> with rasterio.open(raster) as src:
    ...     r_band1_arr = src.read(1)

    >>> assert np.array_equal(r_band1_arr, g_band1_arr)


With the gdal objects you have to manually manage the object's lifecycle

.. code-block:: python

    >>> # osgeo.gdal
    >>> # clean up reference to dateset to close
    >>> del g_band1
    >>> del g_ds

Writing
~~~~~~~

Let's take the arrays that we've read from the original dataset and write them out
to a new GeoTIFF file.

With Rasterio, you open the dataset, read the data and the
``profile`` which contains the metadata necessary to write a similar dataset.

.. code-block:: python

    >>> # rasterio
    >>> with rasterio.open(raster) as src:
    ...     arr = src.read()
    ...     profile = src.profile
    >>> profile['height'], profile['width']
    (718, 791)

 Writing the 3D array with Rasterio is similar to Python's file interface
 with some additional metadata to handle geospatial datasets:

.. code-block:: python

    >>> # rasterio
    >>> with rasterio.open('/tmp/newraster.tif', 'w', **profile) as dst:
    ...     dst.write(arr)
   

 The equivalent operation in osgeo.gdal requires a more procedural approach:

.. code-block:: python

    >>> driver = gdal.GetDriverByName('GTiff')
    >>> out_raster = driver.Create('/tmp/newraster_gdal.tif',
    ...                            profile['width'], profile['height'],
    ...                            profile['count'], gdal.GDT_Byte)
    >>> out_raster.SetGeoTransform(profile['transform'].to_gdal())
    0
    >>> for bidx in range(1, profile['count'] + 1):
    ...     band = out_raster.GetRasterBand(bidx)
    ...     band.WriteArray(arr[bidx - 1])
    ...     band.FlushCache()
    0
    0
    0
    >>> from osgeo import osr
    >>> srs = osr.SpatialReference()
    >>> srs.ImportFromWkt(profile['crs'].wkt)
    0
    >>> out_raster.SetProjection(srs.ExportToWkt())
    0
    >>> out_raster.FlushCache()


For a real-world example of a Python project making the osgeo.gdal-to-rasterio switch,
see the pull request for the `rasterstats migration`_.


.. _rasterstats Migration: https://github.com/perrygeo/python-rasterstats/pull/63
.. _Python Gotchas: https://trac.osgeo.org/gdal/wiki/PythonGotchas

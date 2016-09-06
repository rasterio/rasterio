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

.. code-block:: python

   with rasterio.Env(CPL_DEBUG=True, GDAL_CACHEMAX=512):
       # ...

Dataset Objects
===============

TODO.

Band Objects
============

TODO. Briefly: GDAL has band objects, Rasterio does not.

Geotransforms
=============

TODO

Coordinate Reference Systems
============================

TODO

Offsets and Windows
===================

TODO

Valid Data Masks
================

TODO

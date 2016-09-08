=====================================
Switching from GDAL's Python bindings
=====================================

Switching from GDAL's Python bindings, meaning the ``gdal`` module in the
``osgeo`` namespace, to Rasterio for new projects or new iterations on existing
projects may not be complicated. This document explains the key similarities
and differences between these two Python packages and provides some guidelines
for why and how to switch.

Mutual Incompatibility
======================

Rasterio and GDAL's bindings contend for global GDAL objects. Choose one of
``import osgeo.gdal`` or ``import rasterio``.

GDAL's bindings (``gdal`` for the rest of this document) and Rasterio are
mutually incompatible and should not be imported and used in a single Python
program. The reason is that the dynamic library they each load (these are
C extension modules, remember), ``libgdal.so`` on Linux, ``gdal.dll`` on
Windows, has a number of global objects and the two modules take different,
naive approaches to managing these objects. It is assumed in multiple places in
``gdal`` that no other Python module is modifying the variables in the dynamic
library. Rasterio makes the same kind of assumptions and consequently the state
of global objects like the format driver registry may be unpredictable.
Additionally, ``gdal`` and Rasterio register conflicting error handlers and
thus the propagation of exceptions and warnings may depend on which module was
imported last.

Static linking of the GDAL library for ``gdal`` and ``rasterio`` can avoid
this contention, but in practice you will almost never see distributions of
these modules that statically link GDAL.

Beyond the issues above, the modules have different styles and don't complement
each other well.

The GDAL Environment
====================

GDAL library functions are excuted in a context of format drivers, error
handlers, and format-specific configuration options that this document will
call the "GDAL Environment." Rasterio has an abstraction for the GDAL
environment, ``gdal`` does not.

With ``gdal``, this context is initialized upon import of the module. This
makes sense because ``gdal`` objects are thin wrappers around functions and
classes in the GDAL dynamic library that generally require registration of
drivers and error handlers.  The ``gdal`` module doesn't have an abstraction
for the environment, but it can be modified using functions like
``gdal.SetErrorHandler()`` and ``gdal.UseExceptions()``.

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

Datasets
========

Rasterio uses URIs to identify datasets, with schemes for different protocols.
The GDAL bindings have their own special syntax.

Unix-style filenames such as ``/var/data/example.tif`` identify dataset files
for both Rasterio and ``gdal``. Rasterio also accepts 'file' scheme URIs
like ``file:///var/data/example.tif``.

Rasterio identifies datasets within ZIP or tar archives using Apache VFS style
identifiers like ``zip:///var/data/example.zip!example.tif`` or
``tar:///var/data/example.tar!example.tif``.

Datasets served via HTTPS are identified using 'https' URIs like
``https://landsat-pds.s3.amazonaws.com/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF``.

Datasets on AWS S3 are identified using 's3' scheme identifiers like
``s3://landsat-pds/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF``.

With ``gdal``, the equivalent identifiers are respectively
``/vsizip//var/data/example.zip/example.tif``,
``/vsitar//var/data/example.tar/example.tif``,
``/vsicurl/landsat-pds.s3.amazonaws.com/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF``,
and
``/vsis3/landsat-pds/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF``.

Format Drivers
==============

``gdal`` provides objects for each of the GDAL format drivers. With Rasterio,
format drivers are represented by strings and are used only as arguments to
functions like ``rasterio.open()``.

.. code-block:: python

   dst = rasterio.open('new.tif', 'w', format='GTiff', **kwargs)

Rasterio uses the same format driver names as GDAL does.

Bands
=====

``gdal`` has band objects. Rasterio does not and thus never has objects with
dangling dataset pointers. With Rasterio, bands are represented by a numerical
index, starting from 1, and are used as arguments to dataset methods. To read
the first band of a dataset as a Numpy ``ndarray``, do this.

.. code-block:: python

   with rasterio.open('example.tif') as src:
       band1 = src.read(1)

Other attributes of GDAL band objects generally surface in Rasterio as tuples
returned by dataset attributes, with one value per band, in order.

.. code-block:: pycon

   >>> src = rasterio.open('example.tif')
   >>> src.indexes
   (1, 2, 3)
   >>> src.dtypes
   ('uint8', 'uint8', 'uint8')
   >>> src.descriptions
   ('Red band', 'Green band', 'Blue band')
   >>> src.units
   ('DN', 'DN', 'DN')

Developers that want read-only band objects for their applications can create
them by zipping these tuples together.

.. code-block:: python

   from collections import namedtuple

   Band = namedtuple('Band', ['idx', 'dtype', 'description', 'units'])

   src = rasterio.open('example.tif')
   bands = [Band(vals) for vals in zip(
       src.indexes, src.dtypes, src.descriptions, src.units)]

Namedtuples are like lightweight classes.

.. code-block:: pycon

   >>> for band in bands:
   ...     print(band.idx)
   ...
   1
   2
   3


Geotransforms
=============

The ``transform`` attribute of a Rasterio dataset object is comparable to the
``GeoTransform`` attribute of a GDAL dataset, but Rasterio's has more power.
It's not just an array of affine transformation matrix elements, it's an
instance of an ``Afine`` class and has many handy methods. For example, the
spatial coordinates of the upper left corner of any raster element is the
product of the dataset's ``transform`` matrix and the ``(column, row)`` index
of the element.

.. code-block:: pycon

   >>> src = rasterio.open('example.tif')
   >>> src.transform * (0, 0)
   (101985.0, 2826915.0)

The affine transformation matrix can be inverted as well.

.. code-block:: pycon

   >>> ~src.transform * (101985.0, 2826915.0)
   (0.0, 0.0)

``Affine`` instances can be created from or converted to the sequences used by
``gdal``.

.. code-block:: pycon

    >>> from rasterio.transform import Affine
    >>> Affine.from_gdal(101985.0, 300.0379266750948, 0.0,
    ...                  2826915.0, 0.0, -300.041782729805).to_gdal()
    ...
    (101985.0, 300.0379266750948, 0.0, 2826915.0, 0.0, -300.041782729805)

Coordinate Reference Systems
============================

The ``crs`` attribute of a Rasterio dataset object is an instance of Rasterio's
``CRS`` class and works well with ``pyproj``.

.. code-block:: pycon

   >>> from pyproj import Proj, transform
   >>> src = rasterio.open('example.tif')
   >>> transform(Proj(src.crs), Proj('+init=epsg:3857'), 101985.0, 2826915.0)
   (-8789636.707871985, 2938035.238323653)

Offsets and Windows
===================

Rasterio adds an abstraction for subsets or windows of a raster array that
GDAL does not have.

.. code-block:: python

   src = rasterio.open('example.tif')

   row_start, row_stop = 0, 10
   col_start, col_stop = 0, 10
   subset_window = (
   subset = src.read(1, window=((row_start, row_stop), (col_start, col_stop)))

.. note::

   Rasterio 1.0 will include a new ``Window`` class that makes this abstraction
   easier to use.

Valid Data Masks
================

Rasterio provides an array for every dataset representing its valid data mask
using the same indicators as GDAL: ``0`` for invalid data and ``255`` for valid
data.

.. code-block:: pycon

   >>> src = rasterio.open('example.tif')
   >>> src.dataset_mask()
   array([[0, 0, 0, ..., 0, 0, 0],
          [0, 0, 0, ..., 0, 0, 0],
          [0, 0, 0, ..., 0, 0, 0],
          ...,
          [0, 0, 0, ..., 0, 0, 0],
          [0, 0, 0, ..., 0, 0, 0],
          [0, 0, 0, ..., 0, 0, 0]], dtype=uint8)

Arrays for dataset bands can also be had as a Numpy ``masked_array``.

.. code-block:: pycon

    >>> src.read(1, masked=True)
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

Where the masked array's ``mask`` is ``True``, the data is invalid and has been
masked "out" in the opposite sense of GDAL's mask.

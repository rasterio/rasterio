Migration Guide for osgeo.gdal users
====================================


Differences between rasterio and osgeo.gdal
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Rasterio uses the ``libgdal`` shared library under the hood to provide a significant portion
of functionality.  GDAL itself ships with its own python bindings, ``osgeo.gdal``.
This section will discuss the differences between ``rasterio`` and ``osgeo.gdal``
and reasons why you might choose to use one over the other.

Rasterio is, by design, a library for reading and writing raster datasets.
Rasterio *uses* GDAL but is not a "Python binding for GDAL."

``osgeo.gdal`` is automatically-generated using swig. As a result, the interface and method names are
similar to the C API. Virtually all of the GDAL C API is exposed through the library.

The ``rasterio`` library is built from the ground up to provide an interface for reading,
writing and manipulating geospatial raster data that follows the style and convention
of idiomatic Python code.  We use a selected subset of the GDAL C API in order to
provide this functionality.

In practice, while many similar tasks can be performed by both libraries,
the difference in coding style is significant. For example, opening a raster file
with ``osgeo.gdal`` involves using gdal constants and the programmer must provide
their own error handling and memory management ::

    from osgeo import gdal
    from osgeo.gdalconst import *
    dataset = gdal.Open( filename, GA_ReadOnly )
    if dataset is None:
        # ... handle a non-existant dataset
    # ... work with dataset
    del dataset

Compared to the similar code in ``rasterio``::

    import rasterio
    with rasterio.Env():
        with rasterio.open(filename, 'r') as dataset:
            # ... work with dataset

The ``rasterio`` code:

* Uses pep8 compliant module, method and property names
* Follows the conventions of python file handles
* Uses context managers to safely manage memory, global environment and file resources
* Will raise proper exceptions (i.e. ``RasterioIOError`` if the file does not exist)

``osgeo.gdal`` gotchas
^^^^^^^^^^^^^^^^^^^^^^^

Beyond idiomatic python coding conventions, the need for Rasterio arose as a
result of several quirks of the ``osgeo.gdal`` module which made it difficult to manage
as a software dependency or as part of a production system.

.. todo::

  * global state makes osgeo.gdal unsafe with other python modules
  * hidden behavior with environm vars vs explicit GDALEnv
  * vsi vs URIs
  * installation and packaging issues
  * examples of unsafe memory situations

For a more detailed look at some unexpected behaviors of the ``osgeo.gdal`` module, see the `Python Gotchas`_ page on the GDAL wiki.


Command Line Interface
^^^^^^^^^^^^^^^^^^^^^^

In addition to the python library, Rasterio also provides the ``rio`` command which
contains several subcommands whose functionality overlaps what is provided by
the ``gdal*`` commands

.. todo::
   * differences between similar commands
   * what rio doesn't do
   * what gdal* doesn't do

Migrating
^^^^^^^^^

So maybe we've convinced you to give Rasterio a try. How do you go about migrating an
existing script or a project that uses ``osgeo.gdal`` to ``rasterio``? This section will
walk through several common examples of ``osgeo.gdal`` code and show the equivalent
process using ``rasterio``.


Reading
~~~~~~~
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
    (3, 719, 791)
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

.. todo::

    * write a 3D array to a multiband raster
    * write a 3D subset to a raster with proper georeferencing (affine vs transform discussion)
    * write a 2D array to a single-band raster


For a real-world example of a Python project making the osgeo.gdal-to-rasterio switch,
see the pull request for the `rasterstats migration`_.


.. _rasterstats Migration: https://github.com/perrygeo/python-rasterstats/pull/63
.. _Python Gotchas: https://trac.osgeo.org/gdal/wiki/PythonGotchas

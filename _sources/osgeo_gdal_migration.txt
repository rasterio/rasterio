Migration Guide for osgeo.gdal users
====================================


Differences between rasterio and osgeo.gdal
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Rasterio uses GDAL's shared library under the hood to provide a significant portion of its functionality.
But GDAL also ships with its own python bindings, ``osgeo.gdal``.
This section will discuss the differences between ``rasterio`` and ``osgeo.gdal`` and reasons why you might
choose to use one over the other.

``osgeo.gdal`` is automatically-generated using swig. As a result, the interface and method names are
similar to the native C++ API.  The ``rasterio`` library is built with Cython which allows
us to create an interface that follows the style and conventions of familiar Python code.

This is best illustrated by example.  Opening a raster file with ``osgeo.gdal`` involves using gdal constants and the programmer must provide their own error handling and memory management ::

    from osgeo import gdal
    from osgeo.gdalconst import *
    dataset = gdal.Open( filename, GA_ReadOnly )
    if dataset is None:
        # ... handle a non-existant dataset
    # ... work with dataset
    del dataset

Compared to the similar code in ``rasterio``::

    import rasterio
    with rasterio.drivers():
        with rasterio.open(filename, 'r') as dataset:
            # ... work with dataset

The ``rasterio`` code:

* Uses pep8 compliant module, method and property names
* follows the conventions of python file handles
* uses context managers to safely manage memory, environment variables and file resources
* will raise proper exceptions (i.e. ``IOError`` if the file does not exist)
* uses a driver context to avoid reliance on environment variables to define behavior
* readability is subjective but most Python programmers would agree that the ``rasterio`` example is easier to read and understand.

For a more detailed look at some unexpected behaviors of the ``osgeo.gdal`` module, see the `Python Gotchas`_ page on the GDAL wiki. 

.. todo::

  * global state makes osgeo.gdal unsafe with other python modules
  * hidden behavior with env vars vs explicit GDALEnv
  * vsi vs URIs
  * limited scope of rasterio, what does osgeo.gdal do that rasterio can't
  * installation issues
  * crs handling
  * examples of unsafe memory situations
  * rio and the relationship to gdal CLI tools
  
Migrating
^^^^^^^^^

.. todo::

    Practical tips and examples of porting common use cases in both python and cli.
    Some overlap with the cookbook here, so probably best to reference it when appropriate.

.. _Python Gotchas: https://trac.osgeo.org/gdal/wiki/PythonGotchas

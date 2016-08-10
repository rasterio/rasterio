======================
Rasterio Documentation
======================

Rasterio reads and writes geospatial raster data.

Geographic information systems use GeoTIFF and other formats to organize
and store gridded raster datasets. Rasterio reads and writes these
formats and provides a Python API based on Numpy N-dimensional arrays.

Rasterio supports Python 2.7 and 3.3-3.5 on Linux and Mac OS X.

.. code:: pycon

    >>> dataset = rasterio.open('example.tif')
    >>> dataset.driver
    'GTiff'
    >>> dataset.count
    1
    >>> dataset.dtypes
    ('uint16',)
    >>> dataset.shape
    (7871, 7731)
    >>> dataset.crs
    CRS({'init': 'epsg:32612'})
    >>> dataset.bounds
    BoundingBox(left=358485.0, bottom=4028985.0, right=59

User guide
==========

.. toctree::
   :maxdepth: 2

   user/intro
   user/installation
   user/quickstart
   user/reading
   user/working_with_datasets
   user/writing
   user/osgeo_gdal_migration

Advanced topics
===============

.. toctree::
   :maxdepth: 2

   topics/color
   topics/concurrency
   topics/errors
   topics/features
   topics/fillnodata
   topics/georeferencing
   topics/image_options
   topics/image_processing
   topics/masking-by-shapefile
   topics/masks
   topics/migrating-to-v1
   topics/nodata
   topics/overviews
   topics/plotting
   topics/reproject
   topics/resampling
   topics/tags
   topics/vsi
   topics/windowed-rw

API documentation
=================

.. toctree::
   :maxdepth: 2

   api/index

CLI guide
=========

.. toctree::
   :maxdepth: 2

   cli

Contributor Guide
=================

.. toctree::
   :maxdepth: 2

   contributing

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _GDAL: http://gdal.org/

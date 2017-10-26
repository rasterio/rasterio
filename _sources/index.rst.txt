==========================================
Rasterio: access to geospatial raster data
==========================================

Geographic information systems use GeoTIFF and other formats to organize and
store gridded raster datasets such as satellite imagery and terrain models.
Rasterio reads and writes these formats and provides a Python API based on
Numpy N-dimensional arrays and GeoJSON.

Here's an example program that extracts the GeoJSON shapes of a raster's valid
data footprint.

.. code:: python

    import rasterio
    import rasterio.features
    import rasterio.warp

    with rasterio.open('example.tif') as dataset:

        # Read the dataset's valid data mask as a ndarray.
        mask = dataset.dataset_mask()

        # Extract feature shapes and values from the array.
        for geom, val in rasterio.features.shapes(
                mask, transform=dataset.transform):

            # Transform shapes from the dataset's own coordinate
            # reference system to CRS84 (EPSG:4326).
            geom = rasterio.warp.transform_geom(
                dataset.crs, 'EPSG:4326', geom, precision=6)

            # Print GeoJSON shapes to stdout.
            print(geom)

The output of the program:

.. code:: python

    {'type': 'Polygon', 'coordinates': [[(-77.730817, 25.282335), ...]]}

Rasterio supports Python versions 2.7 and 3.3 or higher.

User guide
==========

Start here with some background about the project and an introduction to 
reading and writing raster datasets.

.. toctree::
   :maxdepth: 2

   intro
   installation
   quickstart
   switch

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
   topics/memory-files
   topics/migrating-to-v1
   topics/nodata
   topics/overviews
   topics/plotting
   topics/reproject
   topics/resampling
   topics/tags
   topics/virtual-warping
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

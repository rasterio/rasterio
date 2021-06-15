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

Rasterio supports Python versions 3.6 or higher.

.. toctree::
   :maxdepth: 2

   intro
   installation
   quickstart
   cli
   topics/index
   api/index
   contributing
   faq

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _GDAL: http://gdal.org/

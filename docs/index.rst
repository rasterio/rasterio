Rasterio Documentation
======================

.. warning::
    This is not the official documentation. Not yet.
    This is a draft and everything here is subject to change.

    For now, please refer to https://github.com/mapbox/rasterio
    for documentation.

Rasterio is for Python programmers and command line users
who want to read, write and manipulate geospatial raster datasets.

Rasterio employs GDAL_ under the hood for file I/O and raster formatting.
Its functions typically accept and return Numpy ndarrays.
Rasterio is designed to make working with geospatial raster data more productive and more fun.

Install with pip (see the complete :doc:`installation docs </installation>` )

.. code::

    pip install rasterio

And an example of use in python

.. code:: python

    import rasterio
    with rasterio.open('data.tif') as src:
        array = src.read()


Contents:

.. toctree::
   :maxdepth: 2

   python_manual
   cli
   api_docs
   community


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _GDAL: http://gdal.org/

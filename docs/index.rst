.. rasterio documentation master file, created by
   sphinx-quickstart on Thu Mar 17 07:05:00 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Rasterio Documentation
======================

Rasterio is for Python programmers and command line users
who want to read, write and manipulate geospatial raster datasets.

Rasterio employs GDAL under the hood for file I/O and raster formatting. Its functions typically accept and return Numpy ndarrays. Rasterio is designed to make working with geospatial raster data more productive and more fun.

You can download from pypi and todo quick link to install

.. code::

    pip install rasterio

And a quick example 

.. code::

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


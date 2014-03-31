Features
========

Rasterio's ``features`` module provides functions to extract shapes of raster
features and to create new features by "burning" shapes into rasters:
``shapes()`` and ``rasterize()``. These functions expose GDAL functions in
a very general way, using iterators over GeoJSON-like Python objects instead of
GIS layers.

Extracting shapes of raster features
------------------------------------

.. image:: https://farm8.staticflickr.com/7018/13547682814_f2e459f7a5_o_d.png

Burning shapes into a raster
----------------------------

.. image:: https://farm4.staticflickr.com/3728/13547425455_79bdb5eaeb_o_d.png


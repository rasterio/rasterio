Reprojection
============

Rasterio can map the pixels of a destination raster with an associated coordinate
reference system and transform to the pixels of a source image with a different
coordinate reference system and transform. This process is known as reprojection.

Rasterio's ``rasterio.warp.reproject()`` is a very geospatial specific analog to
SciPy's ``scipy.ndimage.interpolation.geometric_transform()`` [1]_.

Result
------

https://a.tiles.mapbox.com/v3/sgillies.hfek2oko/page.html?secure=1#6/0.000/0.033

.. [1] http://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.interpolation.geometric_transform.html#scipy.ndimage.interpolation.geometric_transform


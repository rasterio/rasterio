Masks
=====

There are a few different ways for raster datasets to carry valid data masks.
Rasterio subscribes to GDAL's abstract mask band interface, so although the
module's main test dataset has no mask band, GDAL will build one based upon
its declared nodata value.

.. code-block:: python

    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        mask = src.read_mask()
        print mask.any()
        print mask
        print (mask == 0).sum()
        print (mask > 0).sum()

Output:

.. code-block:: console

    True
    [[0 0 0 ..., 0 0 0]
     [0 0 0 ..., 0 0 0]
     [0 0 0 ..., 0 0 0]
     ...,
     [0 0 0 ..., 0 0 0]
     [0 0 0 ..., 0 0 0]
     [0 0 0 ..., 0 0 0]]
    185162
    382776


Resampling
==========

For details on changing coordinate reference systems, see `Reprojection`.

Up and downsampling
-------------------

*Resampling* refers to changing the cell values due to changes in the raster
cell grid. This can occur during reprojection. Even if the projection is not
changing, we may want to change the effective cell size of an existing dataset.

*Upsampling* refers to cases where we are converting to higher
resolution/smaller cells.  *Downsampling* is resampling to lower
resolution/larger cellsizes.

By reading from a raster source into an output array of a different size or by
specifying an *out_shape* of a different size you are effectively resampling
the data.

Here is an example of upsampling by a factor of 2 using the bilinear resampling
method.

.. code-block:: python

    import rasterio
    from rasterio.enums import Resampling

    with rasterio.open("example.tif") as dataset:
        data = dataset.read(
            out_shape=(dataset.height * 2, dataset.width * 2, dataset.count),
            resampling=resampling.bilinear
        )

Here is an example of downsampling by a factor of 2 using the average resampling
method.

.. code-block:: python

    with rasterio.open("example.tif") as dataset:
        data = dataset.read(
            out_shape=(dataset.height / 2, dataset.width / 2, dataset.count),
            resampling=resampling.average
        )

.. note::

   After these resolution changing operations, the dataset's resolution and the
   resolution components of its affine *transform* property no longer apply to
   the new arrays.


Resampling Methods
------------------

When you change the raster cell grid, you must recalulate the pixel values.
There is no "correct" way to do this as all methods involve some interpolation.

The current resampling methods can be found in the `rasterio.enums`_ source.

Of note, the default ``Resampling.nearest`` method may not be suitable for
continuous data. In those cases, ``Resampling.bilinear`` and
``Resampling.cubic`` are better suited.  Some specialized statistical
resampling method exist, e.g. ``Resampling.average``, which may be useful when
certain numerical properties of the data are to be retained.


.. _rasterio.enums: https://github.com/mapbox/rasterio/blob/master/rasterio/enums.py#L28

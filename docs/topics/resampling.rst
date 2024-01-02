Resampling
==========

For details on changing coordinate reference systems, see
:doc:`Reprojection <reproject>`.

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

    upscale_factor = 2

    with rasterio.open("example.tif") as dataset:

        # resample data to target shape
        data = dataset.read(
            out_shape=(
                dataset.count,
                int(dataset.height * upscale_factor),
                int(dataset.width * upscale_factor)
            ),
            resampling=Resampling.bilinear
        )

        # scale image transform
        transform = dataset.transform * dataset.transform.scale(
            (dataset.width / data.shape[-1]),
            (dataset.height / data.shape[-2])
        )

Downsampling to 1/2 of the resolution can be done with ``upscale_factor = 1/2``.


Resampling Methods
------------------

When you change the raster cell grid, you must recalculate the pixel values.
There is no "correct" way to do this as all methods involve some interpolation.

The current resampling methods can be found in the
:class:`rasterio.enums.Resampling` class.

Of note, the default :attr:`~rasterio.enums.Resampling.nearest` method may not
be suitable for continuous data. In those cases,
:attr:`~rasterio.enums.Resampling.bilinear` and
:attr:`~rasterio.enums.Resampling.cubic` are better suited.
Some specialized statistical resampling method exist, e.g.
:attr:`~rasterio.enums.Resampling.average`, which may be useful when
certain numerical properties of the data are to be retained.

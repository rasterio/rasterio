Resampling
==========

For details on changing coordinate reference systems, see `Reprojection`.

Up and Downsampling
-------------------

*Resampling* refers to changing the cell values due to changes in the raster cell grid. This can occur during reprojection. Even if the crs is not changing, we may want to change the effective cell size of an existing dataset.

*Upsampling* refers to cases where we are converting to higher resolution/smaller cells.
*Downsampling* is resampling to lower resolution/larger cellsizes.

There are three potential ways to perform up/downsampling.

Use reproject
~~~~~~~~~~~~~
~
If you use ``reproject`` but keep the same CRS, you can utilize the underlying GDAL algorithms
to resample your data.

This involves coordinating the size of your output array with the
cell size in it's associated affine transform. In other words, if you *multiply* the resolution
by ``x``, you need to *divide* the affine parameters defining the cell size by ``x``

.. code-block:: python

    arr = src.read()
    newarr = np.empty(shape=(arr.shape[0],  # same number of bands
                             round(arr.shape[1] * 1.5), # 150% resolution
                             round(arr.shape[2] * 1.5)))

    # adjust the new affine transform to the 150% smaller cell size
    aff = src.transform
    newaff = Affine(aff.a / 1.5, aff.b, aff.c,
                    aff.d, aff.e / 1.5, aff.f)

    reproject(
        arr, newarr,
        src_transform = aff,
        dst_transform = newaff,
        src_crs = src.crs,
        dst_crs = src.crs,
        resampling = Resampling.bilinear)


Use scipy
~~~~~~~~~

You can also use `scipy.ndimage.interpolation.zoom`_ to "zoom" with a configurable spline interpolation
that differs from the resampling methods available in GDAL. This may not be appropriate for all data so check the results carefully. You must adjust the affine transform just as we did above.

.. code-block:: python

    from scipy.ndimage.interpolation import zoom

    # Increase resolution, decrease cell size by 150%
    # Note we only zoom on axis 1 and 2
    # axis 0 (our band axis) stays fixed
    arr = src.read()
    newarr = zoom(arr, zoom=[1, 1.5, 1.5], order=3, prefilter=False)

    # Adjust original affine transform
    aff = src.transform
    newaff = Affine(aff.a / 1.5, aff.b, aff.c,
                    aff.d, aff.e / 1.5, aff.f)


Use decimated reads
~~~~~~~~~~~~~~~~~~~

Another technique for quickly up/downsampling data is to use decimated reads.
By reading from a raster source into an ``out`` array of a specified size, you
are effectively resampling the data to a new size.

.. warning::

     The underlying GDALRasterIO function does not support different resampling
     methods. You are stuck with the default which can result in unwanted effects
     and data loss in some cases. We recommend using a different method unless
     you are upsampling by an integer factor.

As per the previous two examples, you must also adjust the affine accordingly.

Note that this method is only recommended for *increasing* resolution by an integer factor.

.. code-block:: python

    newarr = np.empty(shape=(arr.shape[0],  # same number of bands
                             round(arr.shape[1] * 2), # double resolution
                             round(arr.shape[2] * 2)))

    arr.read(out=newarr)  # newarr is changed in-place


Resampling Methods
------------------

When you change the raster cell grid, you must recalulate the pixel values. There is no "correct" way to do this as all methods involve some interpolation.

The current resampling methods can be found in the `rasterio.enums`_ source.

Of note, the default ``Resampling.nearest`` method may not be suitable for continuous data. In those
cases, ``Resampling.bilinear`` and ``Resampling.cubic`` are better suited.
Some specialized statistical resampling method exist, e.g. ``Resampling.average``, which may be
useful when certain numerical properties of the data are to be retained.


.. _scipy.ndimage.interpolation.zoom: http://docs.scipy.org/doc/scipy-0.16.1/reference/generated/scipy.ndimage.interpolation.zoom.html
.. _rasterio.enums: https://github.com/mapbox/rasterio/blob/master/rasterio/enums.py#L28

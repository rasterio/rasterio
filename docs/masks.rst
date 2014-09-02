Masks
=====

Reading masks
-------------

There are a few different ways for raster datasets to carry valid data masks.
Rasterio subscribes to GDAL's abstract mask band interface, so although the
module's main test dataset has no mask band, GDAL will build one based upon
its declared nodata value of 0.

.. code-block:: python
    
    import rasterio

    with rasterio.open('tests/data/RGB.byte.tif') as src:
        mask = src.read_mask()
        print mask.any()
        count = mask.shape[0] * mask.shape[1]
        print float((mask > 0).sum())/count
        print float((mask == 0).sum())/count

Some of the elements of the mask evaluate to ``True``, meaning that there is some
valid data. Just over 2/3 of the dataset's pixels (use of sum being a neat trick for
computing the number of pixels in a selection) have valid data.

.. code-block:: console

    True
    0.673974976142
    0.326025023858

Writing masks
-------------

Writing a mask is just as straightforward: pass an ndarray with ``True`` (or values
that evaluate to ``True`` to indicate valid data and ``False`` to indicate no data
to ``write_mask()``.

.. code-block:: python

    import os
    import shutil
    import tempfile

    import numpy
    import rasterio

    tempdir = tempfile.mkdtemp()

    with rasterio.open(
            os.path.join(tempdir, 'example.tif'), 
            'w', 
            driver='GTiff', 
            count=1, 
            dtype=rasterio.uint8, 
            width=10, 
            height=10) as dst:
        
        dst.write_band(1, numpy.ones(dst.shape, dtype=rasterio.uint8))

        mask = numpy.zeros(dst.shape, rasterio.uint8)
        mask[5:,5:] = 255
        dst.write_mask(mask)

    print os.listdir(tempdir)
    shutil.rmtree(tempdir)

The code above masks out all of the file except the lower right quadrant and 
writes a file with a sidecar TIFF to hold the mask.

.. code-block:: console

    ['example.tif', 'example.tif.msk']

To use an internal TIFF mask, use the ``drivers()`` option shown below:

.. code-block:: python

    tempdir = tempfile.mkdtemp()
    tiffname = os.path.join(tempdir, 'example.tif')

    with rasterio.drivers(GDAL_TIFF_INTERNAL_MASK=True):

        with rasterio.open(
                tiffname,
                'w', 
                driver='GTiff', 
                count=1, 
                dtype=rasterio.uint8, 
                width=10, 
                height=10) as dst:
            
            dst.write_band(1, numpy.ones(dst.shape, dtype=rasterio.uint8))

            mask = numpy.zeros(dst.shape, rasterio.uint8)
            mask[5:,5:] = 255
            dst.write_mask(mask)

    print os.listdir(tempdir)
    print subprocess.check_output(['gdalinfo', tiffname])

The output:

.. code-block:: console

    ['example.tif']
    Driver: GTiff/GeoTIFF
    Files: /var/folders/jh/w0mgrfqd1t37n0bcqzt16bnc0000gn/T/tmpcnGV_r/example.tif
    Size is 10, 10
    Coordinate System is `'
    Image Structure Metadata:
      INTERLEAVE=BAND
    Corner Coordinates:
    Upper Left  (    0.0,    0.0)
    Lower Left  (    0.0,   10.0)
    Upper Right (   10.0,    0.0)
    Lower Right (   10.0,   10.0)
    Center      (    5.0,    5.0)
    Band 1 Block=10x10 Type=Byte, ColorInterp=Gray
      Mask Flags: PER_DATASET


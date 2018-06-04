Virtual Warping
===============

Rasterio has a ``WarpedVRT`` class that abstracts many of the details of raster
warping by using an in-memory `Warped VRT
<http://www.gdal.org/gdal_vrttut.html#gdal_vrttut_warped>`__. A ``WarpedVRT`` can
be the easiest solution for tiling large datasets.

For example, to virtually warp the ``RGB.byte.tif`` test dataset from its
proper EPSG:32618 coordinate reference system to EPSG:3857 (Web Mercator) and
extract pixels corresponding to its central zoom 9 tile, do the following.

.. code-block:: python

  from affine import Affine
  import mercantile

  import rasterio
  from rasterio.enums import Resampling
  from rasterio.vrt import WarpedVRT

  with rasterio.open('tests/data/RGB.byte.tif') as src:
      with WarpedVRT(src, crs='EPSG:3857',
                     resampling=Resampling.bilinear) as vrt:

          # Determine the destination tile and its mercator bounds using
          # functions from the mercantile module.
          dst_tile = mercantile.tile(*vrt.lnglat(), 9)
          left, bottom, right, top = mercantile.xy_bounds(*dst_tile)

          # Determine the window to use in reading from the dataset.
          dst_window = vrt.window(left, bottom, right, top)

          # Read into a 3 x 512 x 512 array. Our output tile will be
          # 512 wide x 512 tall.
          data = vrt.read(window=dst_window, out_shape=(3, 512, 512))

          # Use the source's profile as a template for our output file.
          profile = vrt.profile
          profile['width'] = 512
          profile['height'] = 512
          profile['driver'] = 'GTiff'

          # We need determine the appropriate affine transformation matrix
          # for the dataset read window and then scale it by the dimensions
          # of the output array.
          dst_transform = vrt.window_transform(dst_window)
          scaling = Affine.scale(dst_window.num_cols / 512,
                                 dst_window.num_rows / 512)
          dst_transform *= scaling
          profile['transform'] = dst_transform

          # Write the image tile to disk.
          with rasterio.open('/tmp/test-tile.tif', 'w', **profile) as dst:
              dst.write(data)


Normalizing Data to a Consistent Grid
-------------------------------------

A ``WarpedVRT`` can be used to normalize a stack of images with differing
projections, bounds, cell sizes, or dimensions against a regular grid
in a defined bounding box.

The `tests/data/RGB.byte.tif` file is in UTM zone 18, so another file in a
different CRS is required for demonstration.  This command will create a new
image with drastically different dimensions and cell size, and reproject to
WGS84.  As of this writing ``$ rio warp`` implements only a subset of
`$ gdalwarp <http://www.gdal.org/gdalwarp.html>`__'s features, so
``$ gdalwarp`` must be used to achieve the desired transform:

.. code-block:: console

    $ gdalwarp \
        -t_srs EPSG:4326 \
        -te_srs EPSG:32618 \
        -te 101985 2673031 339315 2801254 \
        -ts 200 250 \
        tests/data/RGB.byte.tif \
        tests/data/WGS84-RGB.byte.tif

So, the attributes of these two images drastically differ:

.. code-block:: console

    $ rio info --shape tests/data/RGB.byte.tif
    718 791
    $ rio info --shape tests/data/WGS84-RGB.byte.tif
    250 200
    $ rio info --crs tests/data/RGB.byte.tif
    EPSG:32618
    $ rio info --crs tests/data/WGS84-RGB.byte.tif
    EPSG:4326
    $ rio bounds --bbox --geographic --precision 7 tests/data/RGB.byte.tif
    [-78.95865, 23.5649912, -76.5749237, 25.5508738]
    $ rio bounds --bbox --geographic --precision 7 tests/data/WGS84-RGB.byte.tif
    [-78.9147773, 24.119606, -76.5963819, 25.3192311]

and this snippet demonstrates how to normalize data to consistent dimensions,
CRS, and cell size within a pre-defined bounding box:

.. code-block:: python

    from __future__ import division

    import os

    import affine

    import rasterio
    from rasterio.crs import CRS
    from rasterio.enums import Resampling
    from rasterio import shutil as rio_shutil
    from rasterio.vrt import WarpedVRT


    input_files = (
        # This file is in EPSG:32618
        'tests/data/RGB.byte.tif',
        # This file is in EPSG:4326
        'tests/data/WGS84-RGB.byte.tif'
    )

    # Destination CRS is Web Mercator
    dst_crs = CRS.from_epsg(3857)

    # These coordiantes are in Web Mercator
    dst_bounds = -8744355, 2768114, -8559167, 2908677

    # Output image dimensions
    dst_height = dst_width = 100

    # Output image transform
    left, bottom, right, top = dst_bounds
    xres = (right - left) / dst_width
    yres = (top - bottom) / dst_height
    dst_transform = affine.Affine(xres, 0.0, left,
                                  0.0, -yres, top)

    vrt_options = {
        'resampling': Resampling.cubic,
        'crs': dst_crs,
        'transform': dst_transform,
        'height': dst_height,
        'width': dst_width,
    }

    for path in input_files:

        with rasterio.open(path) as src:

            with WarpedVRT(src, **vrt_options) as vrt:

                # At this point 'vrt' is a full dataset with dimensions,
                # CRS, and spatial extent matching 'vrt_options'.

                # Read all data into memory.
                data = vrt.read()

                # Process the dataset in chunks.  Likely not very efficient.
                for _, window in vrt.block_windows():
                    data = vrt.read(window=window)

                # Dump the aligned data into a new file.  A VRT representing
                # this transformation can also be produced by switching
                # to the VRT driver.
                directory, name = os.path.split(path)
                outfile = os.path.join(directory, 'aligned-{}'.format(name))
                rio_shutil.copy(vrt, outfile, driver='GTiff')

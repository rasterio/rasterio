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
      with WarpedVRT(src, dst_crs='EPSG:3857',
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


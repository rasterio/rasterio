Virtual Warping
===============

Rasterio has a class that abstracts many of the details of raster warping by
using an in-memory `Warped VRT
<http://www.gdal.org/gdal_vrttut.html#gdal_vrttut_warped>`__.

To virtually warp the Rasterio test dataset to EPSG:3857 and extract pixels
corresponding to its central zoom 9 tile, do the following.

.. code-block:: python

  import mercantile

  from rasterio.io import VirtualWarpedFile
  from rasterio.enums import Resampling


  with VirtualWarpedFile('tests/data/RGB.byte.tif', dst_crs='EPSG:3857',
                         resampling=Resampling.bilinear).open() as src:

      # Determine the destination tile and its mercator bounds using
      # functions from the mercantile module.
      dst_tile = mercantile.tile(*src.lnglat(), 9)
      left, top = mercantile.xy(*mercantile.ul(*dst_tile))
      right, bottom = mercantile.xy(*mercantile.ul(
          mercantile.Tile(tile.x + 1, tile.y + 1, tile.z)))

      # Determine the window to use in reading from the dataset.
      dst_window = src.window(left, bottom, right, top)

      # Read into a 3 x 512 x 512 array. Our output tile will be
      # 512 wide x 512 tall.
      data = src.read(window=dst_window, out_shape=(3, 512, 512))

      # Use the source's profile as a template for our output file.
      profile = src.profile
      profile['width'] = 512
      profile['height'] = 512
      profile['driver'] = 'GTiff'

      # We need determine the appropriate affine transformation matrix
      # for the dataset read window and then scale it by the dimensions
      # of the output array.
      dst_transform = src.window_transform(dst_window)
      scaling = Affine.scale(dst_window.num_cols / 512,
                             dst_window.num_rows / 512)
      dst_transform *= scaling
      profile['transform'] = tile_transform

      # Write the image tile to disk.
      with rasterio.open('/tmp/test-tile.tif', 'w', **profile) as dst:
          dst.write(rgb)


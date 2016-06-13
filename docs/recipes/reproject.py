import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio import crs

rgb = 'tests/data/world.tif'
out = '/tmp/reproj.tif'

# Reproject to NAD83(HARN) / Hawaii zone 3 (ftUS) - Transverse Mercator
dst_crs = crs.from_string("EPSG:3759")


with rasterio.Env(CHECK_WITH_INVERT_PROJ=True):
    with rasterio.open(rgb) as src:
        profile = src.profile

        # Calculate the ideal dimensions and transformation in the new crs
        dst_affine, dst_width, dst_height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds)

        # update the relevant parts of the profile
        profile.update({
            'crs': dst_crs,
            'transform': dst_affine,
            'affine': dst_affine,
            'width': dst_width,
            'height': dst_height
        })

        # Reproject and write each band
        with rasterio.open(out, 'w', **profile) as dst:
            for i in range(1, src.count + 1):
                src_array = src.read(i)
                dst_array = np.empty((dst_height, dst_width), dtype='uint8')

                reproject(
                    # Source parameters
                    source=src_array,
                    src_crs=src.crs,
                    src_transform=src.affine,
                    # Destination paramaters
                    destination=dst_array,
                    dst_transform=dst_affine,
                    dst_crs=dst_crs,
                    # Configuration
                    resampling=Resampling.nearest,
                    num_threads=2)

                dst.write(dst_array, i)

import fiona
import rasterio
from rasterio.tools.mask import mask

with fiona.open("tests/data/box.shp", "r") as shapefile:
    geoms = [feature["geometry"] for feature in shapefile]

with rasterio.open("tests/data/RGB.byte.tif") as src:
    out_image, out_transform = mask(src, geoms, crop=True)
    out_meta = src.meta.copy()

out_meta.update({"driver": "GTiff",
                 "height": out_image.shape[1],
                 "width": out_image.shape[2],
                 "transform": out_transform})

with rasterio.open("/tmp/masked.tif", "w", **out_meta) as dest:
    dest.write(out_image)

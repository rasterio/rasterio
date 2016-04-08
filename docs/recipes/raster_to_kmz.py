import os
import zipfile

from affine import Affine
import numpy as np
import rasterio

width = 100
height = 100
count = 3
box_affine = Affine(0.01, 0, -36, 0, -0.01, 75)
crs = {'init': 'epsg:4326'} 
dtype = "uint8"

raster_filename = "/tmp/green_box.tif"
kml_filename = "/tmp/green_box.kml"
kmz_filename = "/tmp/green_box.kmz"
kml_im_path = os.path.join("files", os.path.basename(raster_filename))

with rasterio.open(raster_filename, "w", driver="GTiff", width=width,
                   height=height, count=count, crs=crs, transform=box_affine,
                   dtype=dtype) as dest:
    # initialize a 3 channel uint8 array for our RGB image, and set
    # the green channel to 160, which will produce a solid green image
    data = np.zeros([count, height, width], dtype=dtype)
    data[1, :, :] = 160
    dest.write(data)

with rasterio.open(raster_filename, "r") as src:
    kml_params = {"north": src.bounds.top, "south": src.bounds.bottom,
                  "east": src.bounds.right, "west": src.bounds.left,
                  "kml_im_path": kml_im_path}

# define basic kml string to specify how image is display in google earth
kml_string = """<?xml version="1.0" encoding="utf-8"?>
<kml xmlns="http://earth.google.com/kml/2.1">
  <Folder>
    <name>KMZ from raster</name>
    <GroundOverlay>
       <name>Greenland green box</name>
       <Icon>
          <href>{kml_im_path}</href>
       </Icon>
       <LatLonBox>
          <north>{north}</north>
          <south>{south}</south>
          <east>{east}</east>
          <west>{west}</west>
       </LatLonBox>
    </GroundOverlay>
  </Folder>
</kml>""".format(**kml_params) 

# write kml string and image to the output kmz file
with zipfile.ZipFile(kmz_filename, "w") as kmz:
    kmz.writestr(kml_filename, kml_string)
    kmz.write(raster_filename, kml_im_path)

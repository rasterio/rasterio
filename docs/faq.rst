Frequently Asked Questions
==========================

Where is "ERROR 4: Unable to open EPSG support file gcs.csv" coming from and what does it mean?
-----------------------------------------------------------------------------------------------

The full message is "ERROR 4: Unable to open EPSG support file gcs.csv.  Try
setting the GDAL_DATA environment variable to point to the directory containing
EPSG csv files." The GDAL/OGR library prints this text to your process's stdout
stream when it can not find the gcs.csv data file it needs to interpret spatial
reference system information stored with a dataset. If you've never seen this
before, you can summon this message by setting GDAL_DATA to a bogus value in
your shell and running a command like ogrinfo:

```bash
$ GDAL_DATA="/lol/wut" ogrinfo example.shp -so example
INFO: Open of 'example.shp'
      using driver 'ESRI Shapefile' successful.

Layer name: example
Geometry: Polygon
Feature Count: 67
Extent: (-113.564247, 37.068981) - (-104.970871, 41.996277)
ERROR 4: Unable to open EPSG support file gcs.csv.  Try setting the GDAL_DATA environment variable to point to the directory containing EPSG csv files.
```

If you're using GDAL software acquired by a package management system like apt
or yum, or Homebrew, you can likely eliminate this message and the condition
that causes it by unsetting GDAL_DATA in your environment.

If you see this error message when using Rasterio in a Python program or when
using Rasterio's CLI in a shell script, the solution is to upgrade to version
1.0.18, which almost always sets GDAL_DATA when needed and otherwise leaves it
alone.

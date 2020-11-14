Georeferencing
==============

There are two parts to the georeferencing of raster datasets: the definition
of the local, regional, or global system in which a raster's pixels are
located; and the parameters by which pixel coordinates are transformed into
coordinates in that system.

Coordinate Reference System
---------------------------

The coordinate reference system of a dataset is accessed from its ``crs``
attribute. 

.. code-block:: python

    >>> import rasterio
    >>> src = rasterio.open('tests/data/RGB.byte.tif')
    >>> src.crs
    CRS({'init': 'epsg:32618'})

Rasterio follows pyproj and uses PROJ.4 syntax in dict form as its native
CRS syntax. If you want a WKT representation of the CRS, see the CRS
class's ``wkt`` attribute.

.. code-block:: python

    >>> src.crs.wkt
    'PROJCS["WGS 84 / UTM zone 18N",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",-75],PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","32618"]]'

When opening a new file for writing, you may also use a CRS string as an
argument.

.. code-block:: python

   >>> profile = {'driver': 'GTiff', 'height': 100, 'width': 100, 'count': 1, 'dtype': rasterio.uint8}
   >>> with rasterio.open('/tmp/foo.tif', 'w', crs='EPSG:3857', **profile) as dst:
   ...     pass # write data to this Web Mercator projection dataset.

.. _coordinate-transformation:

Coordinate Transformation
-------------------------

A dataset's pixel coordinate system has its origin at the "upper left" (imagine
it displayed on your screen). Column index increases to the right, and row 
index increases downward. The mapping of these coordinates to "world"
coordinates in the dataset's reference system is done with an affine
transformation matrix.

.. code-block:: pycon

    >>> src.transform
    Affine(300.0379266750948, 0.0, 101985.0,
           0.0, -300.041782729805, 2826915.0)

The ``Affine`` object is a named tuple with elements ``a, b, c, d, e, f``
corresponding to the elements in the matrix equation below, in which 
a pixel's image coordinates are ``x, y`` and its world coordinates are
``x', y'``.::

    | x' |   | a b c | | x |
    | y' | = | d e f | | y |
    | 1  |   | 0 0 1 | | 1 |

The ``Affine`` class has some useful properties and methods
described at https://github.com/sgillies/affine.

Some datasets may not have an affine transformation matrix, but are still georeferenced.

Ground Control Points
----------------------

A ground control point (GCP) is the mapping of a dataset's row and pixel coordinate to a
single world x, y, and optionally z coordinate. Typically a dataset will have multiple
GCPs distributed across the image. Rasterio can calculate an affine transformation matrix
from a collection of GCPs using the ``rasterio.transform.from_gcps`` method.

Rational Polynomial Coefficients
---------------------------------

A dataset may also be georeferenced with a set of rational polynomial coefficients (RPCs)
which can be used to compute pixel coordinates from x, y, and z coordinates. The RPCs are
an application of the Rigorous Projection Model which uses four sets of 20 term cubic polynomials
and several normalizing parameters to establish a relationship between image and world coordinates.
RPCs are defined with image coordinates in pixel units and world coordinates in decimal
degrees of longitude and latitude and height above the WGS84 ellipsoid (EPSG:4326). 

RPCs are usually provided by the dataset provider and are only well behaved over the
extent of the image. Additionally, accurate height values are required for the best
results. Datasets with low terrain variation may use an average height over the extent of
the image, while datasets with higher terrain variation should use a digital elevation
model to sample height values.The coordinate transformation from world to pixel
coordinates is exact while the reverse is not, and must be computed iteratively. For more
details on coordinate transformations using RPCs see
https://gdal.org/api/gdal_alg.html#_CPPv424GDALCreateRPCTransformerP11GDALRPCInfoidPPc
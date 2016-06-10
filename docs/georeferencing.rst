Georeferencing
**************

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
    CRS({'init': u'epsg:32618'})

Rasterio follows pyproj and uses PROJ.4 syntax in dict form as its native
CRS syntax. If you want a WKT representation of the CRS, see the CRS
class's ``wkt`` attribute.

.. code-block:: python

    >>> src.crs.wkt
    u'PROJCS["UTM Zone 18, Northern Hemisphere",GEOGCS["Unknown datum based upon the WGS 84 ellipsoid",DATUM["Not_specified_based_on_WGS_84_spheroid",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4326"]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",-75],PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AUTHORITY["EPSG","32618"]]'

When opening a new file for writing, you may also use a CRS string as an
argument.

.. code-block:: python

   >>> profile = {'driver': 'GTiff', 'height': 100, 'width': 100, 'count': 1, 'dtype': rasterio.uint8}
   >>> with rasterio.open('/tmp/foo.tif', 'w', crs='EPSG:3857', **profile) as dst:
   ...     pass # write data to this Web Mercator projection dataset.

Coordinate Transformation
-------------------------

A dataset's pixel coordinate system has its origin at the "upper left" (imagine
it displayed on your screen). Column index increases to the right, and row 
index increases downward. The mapping of these coordinates to "world"
coordinates in the dataset's reference system is done with an affine
transformation matrix.

.. code-block:: pycon

    >>> src.affine
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

Earlier versions of Rasterio had a ``transform`` attribute which was a 6-element
tuple. This usage is deprecated, please see https://github.com/mapbox/rasterio/issues/86 for details. 
In Rasterio 1.0, the value of a  ``transform`` attribute will be an instance
of ``Affine`` and the ``affine`` attribute will remain as an alias.


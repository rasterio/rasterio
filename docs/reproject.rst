Reprojection
************

TODO calc_default_transform

Rasterio can map the pixels of a destination raster with an associated
coordinate reference system and transform to the pixels of a source image with
a different coordinate reference system and transform. This process is known as
reprojection.

Rasterio's ``rasterio.warp.reproject()`` is a very geospatial-specific analog
to SciPy's ``scipy.ndimage.interpolation.geometric_transform()`` [1]_.

The code below reprojects between two arrays, using no pre-existing GIS
datasets.  ``rasterio.warp.reproject()`` has two positional arguments: source
and destination.  The remaining keyword arguments parameterize the reprojection
transform.

.. code-block:: python

    import numpy
    import rasterio
    from rasterio import Affine as A
    from rasterio.warp import reproject, RESAMPLING

    with rasterio.drivers():

        # As source: a 512 x 512 raster centered on 0 degrees E and 0
        # degrees N, each pixel covering 15".
        rows, cols = src_shape = (512, 512)
        d = 1.0/240 # decimal degrees per pixel
        # The following is equivalent to 
        # A(d, 0, -cols*d/2, 0, -d, rows*d/2).
        src_transform = A.translation(-cols*d/2, rows*d/2) * A.scale(d, -d)
        src_crs = {'init': 'EPSG:4326'}
        source = numpy.ones(src_shape, numpy.uint8)*255

        # Destination: a 1024 x 1024 dataset in Web Mercator (EPSG:3857)
        # with origin at 0.0, 0.0.
        dst_shape = (1024, 1024)
        dst_transform = [-237481.5, 425.0, 0.0, 237536.4, 0.0, -425.0]
        dst_crs = {'init': 'EPSG:3857'}
        destination = numpy.zeros(dst_shape, numpy.uint8)

        reproject(
            source, 
            destination, 
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=RESAMPLING.nearest)

        # Assert that the destination is only partly filled.
        assert destination.any()
        assert not destination.all()


See `examples/reproject.py <https://github.com/mapbox/rasterio/blob/master/examples/reproject.py>`__
for code that writes the destination array to a GeoTIFF file. I've uploaded the
resulting file to a Mapbox map to demonstrate that the reprojection is
correct: https://a.tiles.mapbox.com/v3/sgillies.hfek2oko/page.html?secure=1#6/0.000/0.033.

Reprojecting a GeoTIFF dataset
------------------------------

Reprojecting a GeoTIFF dataset from one coordinate reference system is a common
use case.  Rasterio provides a few utilities to make this even easier:

``transform_bounds()``
transforms the bounding coordinates of the source raster to the target
coordinate reference system, densifiying points along the edges to account
for non-linear transformations of the edges.


``calculate_default_transform()``
transforms bounds to target coordinate system, calculates resolution if not
provided, and returns destination transform and dimensions.


.. code-block:: python

    import numpy
    import rasterio
    from rasterio.warp import calculate_default_transform, reproject, RESAMPLING

    dst_crs = 'EPSG:4326'

    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        affine, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds)
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': dst_crs,
            'transform': affine,
            'affine': affine,
            'width': width,
            'height': height
        })

        with rasterio.open('/tmp/RGB.byte.wgs84.tif', 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.affine,
                    src_crs=src.crs,
                    dst_transform=affine,
                    dst_crs=dst_crs,
                    resampling=RESAMPLING.nearest)


See ``rasterio/rio/warp.py`` for more complex examples of reprojection based on
new bounds, dimensions, and resolution (as well as a command-line interface
described
`here <https://github.com/mapbox/rasterio/blob/master/docs/cli.rst#warp>`__).



It is also possible to use ``reproject()`` to create an output dataset zoomed
out by a factor of 2.  Methods of the ``rasterio.Affine`` class help us generate
the output dataset's transform matrix and, thereby, its spatial extent.

.. code-block:: python

    import numpy
    import rasterio
    from rasterio import Affine as A
    from rasterio.warp import reproject, RESAMPLING

    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        src_transform = src.affine

        # Zoom out by a factor of 2 from the center of the source
        # dataset. The destination transform is the product of the
        # source transform, a translation down and to the right, and
        # a scaling.
        dst_transform = src_transform*A.translation(
            -src.width/2.0, -src.height/2.0)*A.scale(2.0)

        data = src.read()

        kwargs = src.meta
        kwargs['transform'] = dst_transform

        with rasterio.open('/tmp/zoomed-out.tif', 'w', **kwargs) as dst:

            for i, band in enumerate(data, 1):
                dest = numpy.zeros_like(band)

                reproject(
                    band,
                    dest,
                    src_transform=src_transform,
                    src_crs=src.crs,
                    dst_transform=dst_transform,
                    dst_crs=src.crs,
                    resampling=RESAMPLING.nearest)

                dst.write(dest, indexes=i)

.. image:: https://farm8.staticflickr.com/7399/16390100651_54f01b8601_b_d.jpg)

References
----------

.. [1] http://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.interpolation.geometric_transform.html#scipy.ndimage.interpolation.geometric_transform


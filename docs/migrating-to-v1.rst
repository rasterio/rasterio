Migrating to Rasterio 1.0
=========================


affine.Affine() vs. GDAL-style geotransforms
--------------------------------------------

One of the biggest API changes on the road to Rasterio 1.0 is the full
deprecation of GDAL-style geotransforms in favor of the `affine
<https://github.com/sgillies/affine>`__ library.  For reference, an
``affine.Affine()`` looks like:

.. code-block:: python

    affine.Affine(a, b, c,
                  d, e, f)

and a GDAL geotransform looks like:

.. code-block:: python

    (c, a, b, f, d, e)

Fundamentally these two constructs provide the same information, but the
``Affine()`` object is much more useful.

Here's a history of this feature:

1. Originally, functions with a ``transform`` argument expected a GDAL
   geotransform.
2. The introduction of the `affine <https://github.com/sgillies/affine>`__
   library involved creating a temporary ``affine`` argument for
   ``rasterio.open()`` and a ``src.affine`` property.  Users could pass an
   ``Affine()`` to ``affine`` or ``transform``, but a GDAL geotransform passed
   to ``transform`` would issue a deprecation warning.
3. ``src.transform`` remained a GDAL geotransform, but issued a warning.  Users
   were pointed to ``src.affine`` during the transition phase.
4. Since the above changes, several functions have been added to Rasterio that
   accept a ``transform`` argument.  Rather than add an ``affine`` argument to
   each, the ``transform`` argument could be either an ``Affine()`` object or a
   GDAL geotransform, the latter issuing the same deprecation warning.

The original plan was to remove the ``affine`` argument + property, and assume
that the object passed to ``transform`` is an ``Affine()``.
However, after `further discussion
<https://github.com/mapbox/rasterio/pull/763>`__ it was determined that
since ``Affine()`` and GDAL geotransforms are both 6 element tuples users may
experience unexplained errors and outputs, so an exception is raised instead to
better highlight the error.

Moving forward:

* ``rasterio.open()`` will still accept ``affine`` and ``transform``, but the
  former now issues a deprecation warning and the latter raises an exception if
  it does not receive an ``Affine()``.
* If ``rasterio.open()`` receives both ``affine`` and ``transform`` an exception
  is raised.
* ``src.affine`` remains but issues a deprecation warning.
* ``src.transform`` property returns an ``Affine()``.
* All other Rasterio functions with a ``transform`` argument now raise an
  exception if they receive a GDAL geotransform.

The features mentioned above that issue a deprecation warning will eventually
be removed, but a timeline has not yet been developed.

Tickets
```````
* `#86 <https://github.com/mapbox/rasterio/issues/86>`__ - Announcing the
  plan to switch from GDAL geotransforms to ``Affine()``.
* `#763 <https://github.com/mapbox/rasterio/pull/763>`__ - Implementation of the
  migration and some further discussion.


I/O Operations
--------------

Methods related to reading band data and dataset masks have changed in 1.0.


Deprecated: ``rasterio.drivers()``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Previously users could register GDAL's drivers and open a datasource with:

.. code-block:: python

    import rasterio

    with rasterio.drivers():

        with rasterio.open('tests/data/RGB.byte.tif') as src:
            pass

but Rasterio 1.0 contains more interactions with GDAL's environment, so
``rasterio.drivers()`` has been replaced with:

.. code-block:: python

    import rasterio
    import rasterio.env

    with rasterio.Env():

        with rasterio.open('tests/data/RGB.byte.tif') as src:
            pass

Tickets
```````

* `#665 <https://github.com/mapbox/rasterio/pull/665>`__ - Deprecation of
  ``rasterio.drivers()`` and introduction of ``rasterio.Env()``.

Removed: ``src.read_band()``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``read_band()`` method has been replaced by ``read()``, which allows for
faster I/O and reading multiple bands into a single ``numpy.ndarray()``.

For example:

.. code-block:: python

    import numpy as np
    import rasterio

    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = np.array(map(src.read_band, (1, 2, 3)))
        band1 = src.read_band(1)

is now:

.. code-block:: python

    import rasterio

    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = src.read((1, 2, 3))
        band1 = src.read(1)

Tickets
```````

* `# 83 <https://github.com/mapbox/rasterio/issues/83>`__ - Introduction of
  ``src.read()``.
* `#96 <https://github.com/mapbox/rasterio/issues/96>`__,
  `#284 <https://github.com/mapbox/rasterio/pull/284>`__ - Deprecation of
  ``src.read_band()``.


Removed: ``src.read_mask()``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``src.read_mask()`` method produced a single mask for the entire datasource,
but could not handle producing a single mask per band, so it was deprecated in
favor of ``src.read_masks()``, although it has no direct replacement.

Tickets
```````

* `#284 <https://github.com/mapbox/rasterio/pull/284>`__ - Deprecation of
  ``src.read_masks()``.


Moved: Functions for working with dataset windows
-------------------------------------------------

Several functions in the top level ``rasterio`` namespace for working with
dataset windows have been moved to ``rasterio.windows.*``:

* ``rasterio.get_data_window()``
* ``rasterio.window_union()``
* ``rasterio.window_intersection()``
* ``rasterio.windows_intersect()``

Tickets
~~~~~~~

* `#609 <https://github.com/mapbox/rasterio/pull/609>`__ - Introduction of
  ``rasterio.windows``.


Moved: ``rasterio.tool``
------------------------

This module has been removed completely and its contents have been moved to
several different locations:

.. code-block::

    rasterio.tool.show()      -> rasterio.plot.show()
    rasterio.tool.show_hist() -> rasterio.plot.show_hist()
    rasterio.tool.stats()     -> rasterio.rio.insp.stats()
    rasterio.tool.main()      -> rasterio.rio.insp.main()

Tickets
~~~~~~~

* `#609 <https://github.com/mapbox/rasterio/pull/609>`__ - Deprecation of
  ``rasterio.tool``.


Moved: ``rasterio.tools``
-------------------------

This module has been removed completely and its contents have been moved to
several different locations:

.. code-block::

     rasterio.tools.mask.mask()   -> rasterio.mask.mask()
     rasterio.tools.merge.merge() -> rasterio.merge.merge()

Tickets
~~~~~~~

* `#609 <https://github.com/mapbox/rasterio/pull/609>`__ - Deprecation of
  ``rasterio.tools``.


Removed: ``rasterio.warp.RESAMPLING``
-------------------------------------

Replaced with ``rasterio.warp.Resampling``


Signature Changes
-----------------

For both ``rasterio.features.sieve()`` and ``rasterio.features.rasterize()`` the
``output`` argument has been replaced with ``out``.  Previously the use of
``output`` issued a deprecation warning.

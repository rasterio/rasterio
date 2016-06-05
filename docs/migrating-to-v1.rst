Migrating to Rasterio 1.0
=========================


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

    with rasterio.env.Env():

        with rasterio.open('tests/data/RGB.byte.tif') as src:
            pass

Tickets
```````

* `#665 <https://github.com/mapbox/rasterio/pull/665>`__ - Deprecation of
  ``rasterio.drivers()`` and introduction of ``rasterio.env.Env()``.

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

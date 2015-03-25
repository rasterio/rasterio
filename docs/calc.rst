Using rio-calc
==============

Simple raster data processing on the command line is possible using Rasterio's
rio-calc command. It uses the `snuggs <https://github.com/mapbox/snuggs>`__
Numpy S-expression engine. The `snuggs README
<https://github.com/mapbox/snuggs/blob/master/README.rst>`__ explains how
expressions are written and evaluated in general. This document explains
Rasterio-specific details of rio-calc and offers some examples.

Expressions
-----------

Rio-calc expressions look like

.. code-block::

    (func|operator arg [*args])

where ``func`` may be the name of any function in the module ``numpy`` or
one of the rio-calc builtins: ``read``, ``fillnodata``, or ``sieve``; and
``operator`` may be any of the standard Python arithmetic or logical operators.
The arguments may themselves be expressions.

Copying a file
--------------

Here's a trivial example of copying a dataset. The expression ``(read 1)``
evaluates to all bands of the first input dataset, an array with shape 
``(3, 718, 791)`` in this case.

Note: rio-calc's indexes start at ``1``.

.. code-block:: console

    $ rio calc "(read 1)" tests/data/RGB.byte.tif out.tif

Reversing the band order of a file
----------------------------------

The expression ``(read i j)`` evaluates to the j-th band of the i-th input
dataset. The ``asarray`` function collects bands read in reverse order into
an array with shape ``(3, 718, 791)`` for output.

.. code-block:: console

    $ rio calc "(asarray (read 1 3) (read 1 2) (read 1 1))" tests/data/RGB.byte.tif out.tif

Stacking bands of multiple files
--------------------------------

Bands can be read from multiple input files. This example is another (slower)
way to copy a file.

.. code-block:: console

    $ rio calc "(asarray (read 1 1) (read 2 2) (read 3 3))" \
    > tests/data/RGB.byte.tif tests/data/RGB.byte.tif tests/data/RGB.byte.tif \
    > out.tif

Named datasets
--------------

Datasets can be referenced in expressions by name and single bands picked out
using the ``take`` function.

.. code-block:: console

    $ rio calc "(asarray (take a 3) (take a 2) (take a 1))" \
    > --name "a=tests/data/RGB.byte.tif" out.tif

The third example, re-done using names, is:

.. code-block:: console

    $ rio calc "(asarray (take a 1) (take b 2) (take b 3))" \
    > --name "a=tests/data/RGB.byte.tif" --name "b=tests/data/RGB.byte.tif" \
    > --name "c=tests/data/RGB.byte.tif" out.tif

Read and take
-------------

The functions ``read`` and ``take`` overlap a bit in the previous examples but
are rather different. The former involves I/O and the latter does not. You may
also ``take`` from any array, as in this example.

.. code-block:: console

    $ rio calc "(take (read 1) 1)" tests/data/RGB.byte.tif out.tif

Arithmetic operations
---------------------

Arithmetic operations can be performed as with Numpy. Here is an example of
scaling all three bands of a dataset by the same factors.

.. code-block:: console

    $ rio calc "(+ 2 (* 0.95 (read 1)))" tests/data/RGB.byte.tif out.tif


Here is a more complicated example of scaling bands by different factors. 


.. code-block:: console

    $ rio calc "(asarray (+ 2 (* 0.95 (read 1 1))) (+ 3 (* 0.9 (read 1 2))) (+ 4 (* 0.85 (read 1 3))))" tests/data/RGB.byte.tif out.tif

Logical operations
------------------

Logical operations can be used in conjunction with arithemtic operations. In
this example, the output values are 255 wherever the input values are greater
than or equal to 40.

.. code-block:: console

    $ rio calc "(* (>= (read 1) 40) 255)" tests/data/RGB.byte.tif out.tif


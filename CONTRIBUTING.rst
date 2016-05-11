Welcome to the Rasterio project. Here's how we work.

Code of Conduct
===============

First of all: the Rasterio project has a code of conduct. Please read the
CODE_OF_CONDUCT.txt file, it's important to all of us.

Design Principles
=================

TODO

Code Conventions
================

The ``rasterio`` namespace contains both Python and C extension modules. All
C extension modules are written using `Cython <http://cython.org/>`__. The
Cython language is a superset of Python. Cython files end with ``.pyx`` and
``.pxd`` and are where we keep all the code that calls C functions in the GDAL
library.

Rasterio supports Python 2 and Python 3 in the same code base.

We strongly prefer code adhering to `PEP8 <https://www.python.org/dev/peps/pep-0008/>`__.

Tests are mandatory for new features. We use ``pytest``.

We aspire to 100% coverage for Python modules. Coverage of the Cython code is
a future aspiration.

Git Conventions
===============

TODO

Issue Conventions
=================

TODO

Development Environment
=======================

TODO

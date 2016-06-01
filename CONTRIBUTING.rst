Welcome to the Rasterio project. Here's how we work.

Code of Conduct
===============

First of all: the Rasterio project has a code of conduct. Please read the
CODE_OF_CONDUCT.txt file, it's important to all of us.

Rights
======

The BSD license (see LICENSE.txt) applies to all contributions.

Design Principles
=================

Rasterio's API is different from GDAL's API and this is intentional.

- Rasterio is a library for reading and writing raster datasets. Rasterio uses
  GDAL but is not a "Python binding for GDAL."
- Rasterio always prefers Python's built-in protocols and types or Numpy
  protocols and types over concepts from GDAL's data model.
- Rasterio keeps I/O separate from other operations. ``rasterio.open()`` is
  the only library function that operates on filenames and URIs.
  ``dataset.read()``, ``dataset.write()``, and their mask counterparts are
  the methods that perform I/O.
- Rasterio methods and functions should be free of side-effects and hidden
  inputs. This is challenging in practice because GDAL embraces global
  variables.

Code Conventions
================

The ``rasterio`` namespace contains both Python and C extension modules. All
C extension modules are written using `Cython <http://cython.org/>`__. The
Cython language is a superset of Python. Cython files end with ``.pyx`` and
``.pxd`` and are where we keep all the code that calls C functions in the GDAL
library.

Rasterio supports Python 2 and Python 3 in the same code base. We have a
compatibility module named ``five.py``. Renaming it is a to-do.

We strongly prefer code adhering to `PEP8
<https://www.python.org/dev/peps/pep-0008/>`__.

Tests are mandatory for new features. We use ``pytest``. Tests written using
``unittest`` are fine, too.

We aspire to 100% coverage for Python modules. Coverage of the Cython code is
a future aspiration.

Git Conventions
===============

TODO

Issue Conventions
=================

Rasterio is a relatively new project and highly active. We have bugs, both
known and unknown.

Please do a search of existing issues, open and closed, before creating a
new one.

Because Rasterio has C extension modules, bug reports very often hinge on the
following details:

- Operating system type and version (Windows? Ubuntu 12.04? 14.04?)
- The source of the Rasterio distribution you installed (PyPI, Anaconda, or
  somewhere else?)
- The version and source of the GDAL library on your system (UbuntuGIS? 
  Homebrew?)

Please provide these details as well as Rasterio version and tracebacks from
your program. Short scripts and datasets that demonstrate the bug are 
especially helpful!

Rasterio is not at 1.0 yet and issues proposing new features are welcome.

Development Environment
=======================

To develop Rasterio, you will need Python 2.7, 3.4, or 3.5 (SG: I'm largely
developing in a Python 3.5 environment) and a C compiler. Windows compiler
details are forthcoming.

How to extend Python with C or C++ is explained at
https://docs.python.org/3.5/extending/extending.html. All of that applies to
Rasterio development, we're not doing anything extraordinary.

Cloning Rasterio's Git repository is the next step
(see https://github.com/mapbox/rasterio).

Always develop in a `virtual environment
<http://docs.python-guide.org/en/latest/dev/virtualenvs/>`__.

Installing GDAL
---------------

The GDAL library and its headers are required to build Rasterio. We do not
have currently have guidance for any platforms other than Linux and OS X.


On Linux, you should obtain GDAL and its headers using your distro's 
package manager. For Ubuntu the commands are:

.. code-block:: console

    (venv)$ sudo add-apt-repository ppa:ubuntugis/ppa
    (venv)$ sudo apt-get update
    (venv)$ sudo apt-get install libgdal1h gdal-bin libgdal-dev

On OS X, Homebrew is a reliable way to get GDAL.

.. code-block:: console

    $ brew install gdal

Python build requirements
-------------------------

Provision your virtualenv with Rasterio's build requirements. Rasterio's
setup.py script will not run unless Cython and Numpy are installed, so do this
first from the Rasterio repo directory.

.. code-block:: console

    (riodev)$ pip install -U pip
    (riodev)$ pip install -r requirements-dev.txt

Once that's done, install Rasterio in editable mode with the "docs,test"
extras.

.. code-block:: console

    (riodev)$ pip install -e .[docs,test]

Any time you edit a Cython (``.pyx`` or ``.pxd``) file, you'll need to rerun
that command to build the extension modules.

To run the tests:

.. code-block:: console

    (riodev)$ python -m pytest --cov rasterio --cov-report term-missing

OS X details
------------

We recommend 

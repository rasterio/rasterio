============
Introduction
============

Background
----------

Before Rasterio, there was one way to access the many different kind of raster
data files used in the GIS field with Python: the Python bindings distributed
with the geospatial data abstraction library, `GDAL <http://gdal.org/>`__.
These bindings provide almost no abstraction for GDAL's C API and Python
programs using them read and run like C programs.

Rasterio uses the GDAL C API but is not a "Python binding for GDAL." It is
written for a different mindset.

Philosophy
----------

Rasterio is written with a question in mind: what would it be like to have
a geospatial data abstraction in the Python standard library? GDAL's raster
data model has unique qualities but is not too special to be expressed using
standard Python language features. Rasterio uses fewer classes specific to GDAL
and more ordinary mappings, sequences, and generators.

Rasterio aspires to keep input/output separate from other operations.
``rasterio.open()`` is the only library function that operates on filenames and
URIs. ``dataset.read()``, ``dataset.write()``, and their mask counterparts are
the methods that do I/O.

Rasterio methods and functions avoid hidden inputs and side-effects. GDAL's
C API uses global variables liberally, but Rasterio provides abstractions that
make them less dangerous.

Rasterio delegates calculation of raster data properties almost entirely to
Numpy and uses GDAL mainly for input/output. In the GDAL data model the mean,
minimum, and maximum values of a raster band, for example, are attributes of
a GDAL dataset object. In the Rasterio model they are not attributes of
a Rasterio dataset, but are attributes of the N-D array returned by
``dataset.read()``. Thus Rasterio objects are more limited than GDAL objects.

Rasterio license
----------------

Copyright (c) 2016, MapBox
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of Mapbox nor the names of its contributors may
  be used to endorse or promote products derived from this software without
  specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

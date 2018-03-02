============
Introduction
============

Philosophy
----------

Before Rasterio there was one Python option for accessing the many different
kind of raster data files used in the GIS field: the Python bindings
distributed with the `Geospatial Data Abstraction Library, GDAL
<http://gdal.org/>`__.  These bindings extend Python, but provide little
abstraction for GDAL's C API. This means that Python programs using them tend
to read and run like C programs. For example, GDAL's Python bindings require
users to watch out for dangling C pointers, potential crashers of programs.
This is bad: among other considerations we've chosen Python instead of C to
avoid problems with pointers.

What would it be like to have a geospatial data abstraction in the Python
standard library? One that used modern Python language features and idioms?
One that freed users from concern about dangling pointers and other
C programming pitfalls? Rasterio's goal is to be this kind of raster data
library – expressing GDAL's data model using fewer non-idiomatic extension
classes and more idiomatic Python types and protocols, while performing as
fast as GDAL's Python bindings.

High performance, lower cognitive load, cleaner and more transparent code.
This is what Rasterio is about.

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

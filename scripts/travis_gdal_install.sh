#!/bin/sh
#
# originally contributed by @rbuffat to Toblerity/Fiona
set -ex

GDALOPTS="  --with-ogr \
            --with-geos \
            --with-expat \
            --without-libtool \
            --with-libz=internal \
            --with-libtiff=internal \
            --with-geotiff=internal \
            --without-gif \
            --without-pg \
            --without-grass \
            --without-libgrass \
            --without-cfitsio \
            --without-pcraster \
            --without-netcdf \
            --without-png \
            --with-jpeg=internal \
            --without-gif \
            --without-ogdi \
            --without-fme \
            --without-hdf4 \
            --without-hdf5 \
            --without-jasper \
            --without-ecw \
            --without-kakadu \
            --without-mrsid \
            --without-jp2mrsid \
            --without-bsb \
            --without-grib \
            --without-mysql \
            --without-ingres \
            --without-xerces \
            --without-odbc \
            --without-curl \
            --without-sqlite3 \
            --without-dwgdirect \
            --without-idb \
            --without-sde \
            --without-perl \
            --without-php \
            --without-ruby \
            --without-python"

# Create build dir if not exists
if [ ! -d "$GDALBUILD" ]; then
  mkdir $GDALBUILD;
fi

if [ ! -d "$GDALINST" ]; then
  mkdir $GDALINST;
fi

ls -l $GDALINST

# download and compile gdal version
if [ ! -d $GDALINST/gdal-1.9.2 ]; then
  cd $GDALBUILD
  wget http://download.osgeo.org/gdal/gdal-1.9.2.tar.gz
  tar -xzvf gdal-1.9.2.tar.gz
  cd gdal-1.9.2
  ./configure --prefix=$GDALINST/gdal-1.9.2 $GDALOPTS
  make -j 2
  make install
fi

if [ ! -d $GDALINST/gdal-1.11.2 ]; then
  cd $GDALBUILD
  wget http://download.osgeo.org/gdal/1.11.2/gdal-1.11.2.tar.gz
  tar -xzvf gdal-1.11.2.tar.gz
  cd gdal-1.11.2
  ./configure --prefix=$GDALINST/gdal-1.11.2 $GDALOPTS
  make -j 2
  make install
fi

if [ ! -d $GDALINST/gdal-2.0.1 ]; then
  cd $GDALBUILD
  wget http://download.osgeo.org/gdal/2.0.1/gdal-2.0.1.tar.gz
  tar -xzvf gdal-2.0.1.tar.gz
  cd gdal-2.0.1
  ./configure --prefix=$GDALINST/gdal-2.0.1 $GDALOPTS
  make -j 2
  make install
fi

# change back to travis build dir
cd $TRAVIS_BUILD_DIR

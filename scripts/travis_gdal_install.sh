#!/bin/sh
#
# originally contributed by @rbuffat to Toblerity/Fiona
set -e

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
            --with-netcdf \
            --with-png=internal \
            --with-jpeg=internal \
            --without-gif \
            --without-ogdi \
            --without-fme \
            --without-hdf4 \
            --with-hdf5 \
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
            --with-curl \
            --without-sqlite3 \
            --without-dwgdirect \
            --without-idb \
            --without-sde \
            --without-perl \
            --without-php \
            --without-ruby \
            --without-python \
            --with-static-proj4=/usr/lib"

# Create build dir if not exists
if [ ! -d "$GDALBUILD" ]; then
  mkdir $GDALBUILD;
fi

if [ ! -d "$GDALINST" ]; then
  mkdir $GDALINST;
fi

ls -l $GDALINST

if [ "$GDALVERSION" = "master" ]; then
  cd $GDALBUILD
  git clone --depth 1 https://github.com/OSGeo/gdal gdal-$GDALVERSION
  cd gdal-$GDALVERSION/gdal
  git rev-parse HEAD > newrev.txt
  BUILD=no
  # Only build if nothing cached or if the GDAL revision changed
  if test ! -f $GDALINST/gdal-$GDALVERSION/rev.txt; then
    BUILD=yes
  elif ! diff newrev.txt $GDALINST/gdal-$GDALVERSION/rev.txt >/dev/null; then
    BUILD=yes
  fi
  if test "$BUILD" = "yes"; then
    mkdir -p $GDALINST/gdal-$GDALVERSION
    cp newrev.txt $GDALINST/gdal-$GDALVERSION/rev.txt
    ./configure --prefix=$GDALINST/gdal-$GDALVERSION $GDALOPTS
    make
    make install
  fi
fi

if [ "$GDALVERSION" != "master" -a ! -d "$GDALINST/gdal-$GDALVERSION" ]; then
  cd $GDALBUILD
  wget http://download.osgeo.org/gdal/$GDALVERSION/gdal-$GDALVERSION.tar.gz
  tar -xzf gdal-$GDALVERSION.tar.gz
  cd gdal-$GDALVERSION
  ./configure --prefix=$GDALINST/gdal-$GDALVERSION $GDALOPTS
  make
  make install
fi

# change back to travis build dir
cd $TRAVIS_BUILD_DIR

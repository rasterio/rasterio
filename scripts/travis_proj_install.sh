#!/bin/sh
set -e

if [ "$GDALVERSION" == "master" ] || [ "$GDALVERSION" == "3"* ]; then
    PROJVERSION=6.1.0;
else
    PROJVERSION=4.8.0;
fi

# Create build dir if not exists
if [ ! -d "$PROJBUILD" ]; then
  mkdir $PROJBUILD;
fi

if [ ! -d "$PROJINST" ]; then
  mkdir $PROJINST;
fi

ls -l $PROJINST

echo "PROJ VERSION: $PROJVERSION"

cd $PROJBUILD
wget -q https://download.osgeo.org/proj/proj-$PROJVERSION.tar.gz
tar -xzf proj-$PROJVERSION.tar.gz
cd proj-$PROJVERSION
./configure --prefix=$PROJINST
make -s -j 2
make install

# change back to travis build dir
cd $TRAVIS_BUILD_DIR

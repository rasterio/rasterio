#!/bin/sh
set -e

PROJVERSION=6.1.0

# Create build dir if not exists
if [ ! -d "$PROJBUILD" ]; then
  mkdir $PROJBUILD;
fi


cd $PROJBUILD
wget -q https://download.osgeo.org/proj/proj-$PROJVERSION.tar.gz
tar -xzf proj-$PROJVERSION.tar.gz
cd proj-$PROJVERSION
./configure
make -s -j 2
make install

# change back to travis build dir
cd $TRAVIS_BUILD_DIR

PROJ_VERSION=9.7.0
GDAL_VERSION=3.11.5
SQLITE_VERSION=3500400
OPENSSL_VERSION=3.6.0
CURL_VERSION=8.16.0
ZLIB_VERSION=1.3.1
TIFF_VERSION=4.7.1
NGHTTP2_VERSION=1.65.0
LERC_VERSION=4.0.0
JPEG_VERSION=9f
LIBWEBP_VERSION=1.6.0
ZSTD_VERSION=1.5.7
LIBPNG_VERSION=1.6.50
OPENJPEG_VERSION=2.5.3
GIFLIB_VERSION=5.2.2
JSONC_VERSION=0.18
XZ_VERSION=5.8.1
LCMS2_VERSION=2.17
HDF5_VERSION=1.14.6
LIBAEC_VERSION=1.1.3
NETCDF_VERSION=4.9.3
GEOS_VERSION=3.14.1
BLOSC_VERSION=1.21.6
PCRE_VERSION=10.47
EXPAT_VERSION=2.7.3
LIBDEFLATE_VERSION=1.24


BUILD_PREFIX="${BUILD_PREFIX:-/usr/local}"

export GDAL_CONFIG="$BUILD_PREFIX/bin/gdal-config"
export PROJ_DATA="$BUILD_PREFIX/share/proj"

echo "BUILD_PREFIX:"
echo "$BUILD_PREFIX"
echo "GDAL_CONFIG:"
echo "$GDAL_CONFIG"
echo "PROJ_DATA:"
echo "$PROJ_DATA"

set -e

# 🔍 Detect OS and architecture
OS="$(uname -s)"
ARCH="$(uname -m)"

# 🧠 Normalize OS
case "$OS" in
    Darwin)
        OS="macos"
        IS_MACOS=1
        ;;
    Linux)
        OS="linux"
        ;;
    *)
        echo "❌ Unsupported OS: $OS"
        exit 1
        ;;
esac

PLATFORM="${OS}-${ARCH}"
echo "✅ Detected platform: $PLATFORM"

# 📦 Set OpenSSL Configure target
case "$PLATFORM" in
    macos-arm64)    TARGET="darwin64-${CMAKE_OSX_ARCHITECTURES}-cc" ;;
    macos-x86_64)   TARGET="darwin64-x86_64-cc" ;;
    linux-aarch64)  TARGET="linux-aarch64" ;;
    linux-x86_64)   TARGET="linux-x86_64" ;;
    *) echo "❌ Unsupported platform: $PLATFORM"; exit 1 ;;
esac

echo "IS_MACOS: ${IS_MACOS}"

# ------------------------------------------------
# From:
#	 https://github.com/rasterio/rasterio-wheels
#    https://github.com/multi-build/multibuild
#
#    (customized and updated)
# ------------------------------------------------


if [ -z "$IS_MACOS" ]; then
    # Strip all binaries after compilation.
    STRIP_FLAGS=${STRIP_FLAGS:-"-Wl,-strip-all"}
    export CFLAGS="${CFLAGS:-$STRIP_FLAGS}"
    export CXXFLAGS="${CXXFLAGS:-$STRIP_FLAGS}"
    export FFLAGS="${FFLAGS:-$STRIP_FLAGS}"
fi

if [ -n "$IS_MACOS" ]; then
    export CFLAGS="$CFLAGS -arch $CMAKE_OSX_ARCHITECTURES -g -O2"
    export CXXFLAGS="$CXXFLAGS -arch $CMAKE_OSX_ARCHITECTURES -g -O2"
    lib_ext="dylib"
else
    export CFLAGS="$CFLAGS -g -O2"
    export CXXFLAGS="$CXXFLAGS -g -O2"
    lib_ext="so"
fi

echo "Flags:"
echo "$CFLAGS"
echo "$CXXFLAGS"

export CPPFLAGS_BACKUP="$CPPFLAGS"
export LIBRARY_PATH_BACKUP="$LIBRARY_PATH"
export PKG_CONFIG_PATH_BACKUP="$PKG_CONFIG_PATH"



function suppress {
    # Run a command, show output only if return code not 0.
    # Takes into account state of -e option.
    # Compare
    # https://unix.stackexchange.com/questions/256120/how-can-i-suppress-output-only-if-the-command-succeeds#256122
    # Set -e stuff agonized over in
    # https://unix.stackexchange.com/questions/296526/set-e-in-a-subshell
    local tmp=$(mktemp tmp.XXXXXXXXX) || return
    local errexit_set
    echo "Running $@"
    if [[ $- = *e* ]]; then errexit_set=true; fi
    set +e
    ( if [[ -n $errexit_set ]]; then set -e; fi; "$@"  > "$tmp" 2>&1 ) ; ret=$?
    [ "$ret" -eq 0 ] || cat "$tmp"
    rm -f "$tmp"
    if [[ -n $errexit_set ]]; then set -e; fi
    return "$ret"
}


function update_env_for_build_prefix {
  # Promote BUILD_PREFIX on search path to any newly built libs
  export CPPFLAGS="-I$BUILD_PREFIX/include $CPPFLAGS_BACKUP"
  export LIBRARY_PATH="$BUILD_PREFIX/lib:$LIBRARY_PATH_BACKUP"
  export PKG_CONFIG_PATH="$BUILD_PREFIX/lib/pkgconfig/:$PKG_CONFIG_PATH_BACKUP"
  # Add binary path for configure utils etc
  export PATH="$BUILD_PREFIX/bin:$PATH"
}


function build_hdf5 {
    if [ -e hdf5-stamp ]; then return; fi
    build_zlib
    # libaec is a drop-in replacement for szip
    build_libaec
    HDF5_VERSION_UNDERSCORED="${HDF5_VERSION//./_}"
    HDF5_VERSION_SHORT="${HDF5_VERSION_UNDERSCORED%_*}"
    wget https://support.hdfgroup.org/releases/hdf5/v${HDF5_VERSION_SHORT}/v${HDF5_VERSION_UNDERSCORED}/downloads/hdf5-${HDF5_VERSION}.tar.gz
    tar -xzf hdf5-${HDF5_VERSION}.tar.gz
    (cd hdf5-${HDF5_VERSION} \
        && export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$BUILD_PREFIX/lib \
        && export DYLD_LIBRARY_PATH=$DYLD_LIBRARY_PATH:$BUILD_PREFIX/lib \
        && ./configure --with-szlib=$BUILD_PREFIX --prefix=$BUILD_PREFIX \
        --enable-threadsafe --enable-unsupported --with-pthread=yes \
        && make -j4 \
        && make install)
    touch hdf5-stamp
}


function build_blosc {
    if [ -e blosc-stamp ]; then return; fi
    local cmake=cmake
    BLOSC_URL="https://github.com/Blosc/c-blosc/archive/refs/tags/v${BLOSC_VERSION}.tar.gz"
    wget "$BLOSC_URL" -O "c-blosc-${BLOSC_VERSION}.tar.gz"
    tar -xzf "c-blosc-${BLOSC_VERSION}.tar.gz"
    (cd c-blosc-${BLOSC_VERSION} \
        && $cmake -DCMAKE_INSTALL_PREFIX=$BUILD_PREFIX -DCMAKE_POLICY_VERSION_MINIMUM=3.5 . \
        && make install)
    if [ -n "$IS_MACOS" ]; then
        # Fix blosc library id bug
        for lib in $(ls ${BUILD_PREFIX}/lib/libblosc*.dylib); do
            install_name_tool -id $lib $lib
        done
    fi
    touch blosc-stamp
}


function build_geos {

    if [ -e geos-stamp ]; then return; fi
    local cmake=cmake
    wget http://download.osgeo.org/geos/geos-${GEOS_VERSION}.tar.bz2
    tar -xjf geos-${GEOS_VERSION}.tar.bz2
    (cd geos-${GEOS_VERSION} \
        && mkdir build && cd build \
        && $cmake .. \
        -DCMAKE_INSTALL_PREFIX:PATH=$BUILD_PREFIX \
        -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
	    -DCMAKE_OSX_DEPLOYMENT_TARGET=$MACOSX_DEPLOYMENT_TARGET \
	    -DCMAKE_OSX_ARCHITECTURES=$CMAKE_OSX_ARCHITECTURES \
        -DBUILD_SHARED_LIBS=ON \
        -DCMAKE_BUILD_TYPE=Release \
        -DENABLE_IPO=ON \
        -DBUILD_APPS:BOOL=OFF \
        -DBUILD_TESTING:BOOL=OFF \
        && $cmake --build . -j4 \
        && $cmake --install .)
    touch geos-stamp
}


function build_jsonc {
    if [ -e jsonc-stamp ]; then return; fi
    local cmake=cmake
    wget https://s3.amazonaws.com/json-c_releases/releases/json-c-${JSONC_VERSION}.tar.gz
    tar -xzf json-c-${JSONC_VERSION}.tar.gz
    (cd json-c-${JSONC_VERSION} \
        && $cmake -DCMAKE_INSTALL_PREFIX=$BUILD_PREFIX -DCMAKE_OSX_DEPLOYMENT_TARGET=$MACOSX_DEPLOYMENT_TARGET -DCMAKE_POLICY_VERSION_MINIMUM=3.5 . \
        && make -j4 \
        && make install)
    if [ -n "$IS_MACOS" ]; then
        for lib in $(ls ${BUILD_PREFIX}/lib/libjson-c.5*.dylib); do
            install_name_tool -id $lib $lib
        done
        for lib in $(ls ${BUILD_PREFIX}/lib/libjson-c.dylib); do
            install_name_tool -id $lib $lib
        done
    fi
    touch jsonc-stamp
}


function build_proj {
    CFLAGS="$CFLAGS -DPROJ_RENAME_SYMBOLS"
    CXXFLAGS="$CXXFLAGS -DPROJ_RENAME_SYMBOLS -DPROJ_INTERNAL_CPP_NAMESPACE"
    if [ -e proj-stamp ]; then return; fi
    
    wget https://download.osgeo.org/proj/proj-${PROJ_VERSION}.tar.gz
    tar -xzf proj-${PROJ_VERSION}.tar.gz

    local cmake=cmake
    (cd proj-${PROJ_VERSION} \
        && $cmake . \
        -DCMAKE_INSTALL_PREFIX:PATH=$BUILD_PREFIX \
        -DCMAKE_PREFIX_PATH=${BUILD_PREFIX} \
        -DCMAKE_INCLUDE_PATH=$BUILD_PREFIX/include \
        -DSQLite3_INCLUDE_DIR=$BUILD_PREFIX/include \
        -DSQLite3_LIBRARY=$BUILD_PREFIX/lib/libsqlite3.$lib_ext \
        -DCMAKE_OSX_DEPLOYMENT_TARGET=$MACOSX_DEPLOYMENT_TARGET \
        -DCMAKE_OSX_ARCHITECTURES=$CMAKE_OSX_ARCHITECTURES \
        -DBUILD_SHARED_LIBS=ON \
        -DCMAKE_BUILD_TYPE=Release \
        -DENABLE_IPO=ON \
        -DBUILD_APPS:BOOL=OFF \
        -DBUILD_TESTING:BOOL=OFF \
        && $cmake --build . -j$(nproc) \
        && $cmake --install .)
    touch proj-stamp
}


function build_sqlite {

  if [ -z "$IS_MACOS" ]; then
        CFLAGS="$CFLAGS -DHAVE_PREAD64 -DHAVE_PWRITE64"
  fi

  if [ -e sqlite-stamp ]; then return; fi
  wget https://www.sqlite.org/2025/sqlite-autoconf-${SQLITE_VERSION}.tar.gz
  tar -xzf sqlite-autoconf-${SQLITE_VERSION}.tar.gz

  (cd sqlite-autoconf-${SQLITE_VERSION} \
        && ./configure --enable-rtree --enable-threadsafe --prefix=$BUILD_PREFIX \
        && make \
        && make install)
  touch sqlite-stamp
}


function build_expat {
    if [ -e expat-stamp ]; then return; fi
    if [ -n "$IS_MACOS" ]; then
        :
    else

    EXPAT_VERSION_UNDERSCORED="${EXPAT_VERSION//./_}"
	wget https://github.com/libexpat/libexpat/releases/download/R_${EXPAT_VERSION_UNDERSCORED}/expat-${EXPAT_VERSION}.tar.bz2
    tar -xjf expat-${EXPAT_VERSION}.tar.bz2
        (cd expat-${EXPAT_VERSION} \
            && ./configure --prefix=$BUILD_PREFIX \
            && make -j4 \
            && make install)
    fi
    touch expat-stamp
}


function build_lerc {

	if [ -e lerc-stamp ]; then return; fi
    local cmake=cmake
    wget https://github.com/Esri/lerc/archive/refs/tags/v${LERC_VERSION}.tar.gz -O lerc-$LERC_VERSION.tar.gz
    tar -xzf lerc-${LERC_VERSION}.tar.gz
    (cd lerc-${LERC_VERSION} \
        && mkdir cmake_build && cd cmake_build \
        && $cmake .. \
        -DCMAKE_INSTALL_PREFIX=$BUILD_PREFIX \
        -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
	    -DCMAKE_OSX_DEPLOYMENT_TARGET=$MACOSX_DEPLOYMENT_TARGET \
	    -DCMAKE_OSX_ARCHITECTURES=$CMAKE_OSX_ARCHITECTURES \
        -DBUILD_SHARED_LIBS=ON \
        -DCMAKE_BUILD_TYPE=Release \
        -DENABLE_IPO=ON \
        && $cmake --build . -j4 \
        && $cmake --install .)
    touch lerc-stamp
}

function build_tiff {

    if [ -e tiff-stamp ]; then return; fi
    local cmake=cmake
    build_lerc
    build_jpeg
    build_libwebp
    build_zlib
    build_zstd
    build_xz
    wget https://download.osgeo.org/libtiff/tiff-${TIFF_VERSION}.tar.gz
    tar -xvf tiff-${TIFF_VERSION}.tar.gz

    (cd tiff-${TIFF_VERSION} \
        && ./configure --prefix=$BUILD_PREFIX --libdir=$BUILD_PREFIX/lib --enable-zstd --enable-webp --enable-lerc --with-jpeg-include-dir=$BUILD_PREFIX/include --with-jpeg-lib-dir=$BUILD_PREFIX/lib \
        && make -j4 \
        && make install)
    touch tiff-stamp
}

function build_openjpeg {

  if [ -e openjpeg-stamp ]; then return; fi

   build_zlib
   build_tiff
   build_lcms2

   wget https://github.com/uclouvain/openjpeg/archive/refs/tags/v${OPENJPEG_VERSION}.tar.gz -O openjpeg-${OPENJPEG_VERSION}.tar.gz
   tar -xvzf openjpeg-${OPENJPEG_VERSION}.tar.gz
   local cmake=cmake
  (cd openjpeg-${OPENJPEG_VERSION} \
        && mkdir build \
        && cd build \
        && $cmake .. \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=$BUILD_PREFIX \
        -DCMAKE_PREFIX_PATH=${BUILD_PREFIX} \
        -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
        -DCMAKE_OSX_DEPLOYMENT_TARGET=$MACOSX_DEPLOYMENT_TARGET \
        -DCMAKE_OSX_ARCHITECTURES=$CMAKE_OSX_ARCHITECTURES \
        && $cmake --build . -j$(nproc) \
        && $cmake --install .)

    touch openjpeg-stamp
}


function build_libwebp {

    build_libpng
    build_giflib

    if [ -e libwebp-stamp ]; then return; fi
    wget https://github.com/webmproject/libwebp/archive/refs/tags/v$LIBWEBP_VERSION.tar.gz -O libwebp-$LIBWEBP_VERSION.tar.gz
    tar -xzf libwebp-$LIBWEBP_VERSION.tar.gz

    (cd libwebp-$LIBWEBP_VERSION \
       && ./autogen.sh \
       && ./configure --prefix=$BUILD_PREFIX \
                      --enable-libwebpmux \
                      --enable-libwebpdemux \
       && make \
       && make install)
    touch libwebp-stamp
}


function build_nghttp2 {
    if [ -e nghttp2-stamp ]; then return; fi
    wget https://github.com/nghttp2/nghttp2/releases/download/v${NGHTTP2_VERSION}/nghttp2-${NGHTTP2_VERSION}.tar.gz
    tar -xzf nghttp2-${NGHTTP2_VERSION}.tar.gz
    (cd nghttp2-${NGHTTP2_VERSION}  \
        && ./configure --enable-lib-only --prefix=$BUILD_PREFIX \
        && make -j4 \
        && make install)
    touch nghttp2-stamp
}


function build_openssl {
    if [ -e openssl-stamp ]; then return; fi

    TAR_FILE="openssl-$OPENSSL_VERSION.tar.gz"
    SHA_FILE="openssl-$OPENSSL_VERSION.tar.gz.sha256"
    wget https://github.com/openssl/openssl/releases/download/openssl-$OPENSSL_VERSION/openssl-$OPENSSL_VERSION.tar.gz
    wget https://github.com/openssl/openssl/releases/download/openssl-$OPENSSL_VERSION/openssl-$OPENSSL_VERSION.tar.gz.sha256

    EXPECTED_HASH=$(cut -d ' ' -f1 "$SHA_FILE")
    ACTUAL_HASH=$(sha256sum "$TAR_FILE" | cut -d ' ' -f1)
    echo "Expected hash: $EXPECTED_HASH"
    echo "Actual hash: $ACTUAL_HASH"
   # Compare hashes
   if [ "$EXPECTED_HASH" == "$ACTUAL_HASH" ]; then

      echo "SHA256 hash verified. Extracting..."
      tar -xzf "$TAR_FILE"
   else
      echo "Hash mismatch! Aborting."
      exit 1
   fi
   (cd openssl-${OPENSSL_VERSION} \
        && ./config $TARGET -fPIC --prefix=$BUILD_PREFIX \
        && make -j4 \
        && make install)
    touch openssl-stamp
}


function build_curl {
    if [ -e curl-stamp ]; then return; fi

    suppress build_openssl
    build_nghttp2
    local flags="--prefix=$BUILD_PREFIX --with-nghttp2=$BUILD_PREFIX --with-zlib=$BUILD_PREFIX --with-ssl=$BUILD_PREFIX --enable-shared --without-libidn2 --without-libpsl"
    wget https://curl.se/download/curl-${CURL_VERSION}.tar.gz
    tar -xzvf curl-${CURL_VERSION}.tar.gz
    (cd curl-${CURL_VERSION} \
        && LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$BUILD_PREFIX/lib:$BUILD_PREFIX/lib64 \
        && DYLD_LIBRARY_PATH=$DYLD_LIBRARY_PATH:$BUILD_PREFIX/lib ./configure $flags \
        && make -j4 \
        && if [ -n "$IS_MACOS" ]; then make install; else make install; fi)
    touch curl-stamp
}


function build_zstd {

    if [ -e zstd-stamp ]; then return; fi
    wget https://github.com/facebook/zstd/archive/v${ZSTD_VERSION}.tar.gz -O zstd-$ZSTD_VERSION.tar.gz
    tar -xzf zstd-${ZSTD_VERSION}.tar.gz

    if [ -n "$IS_MACOS" ]; then
        sed_ere_opt="-E"
    else
        sed_ere_opt="-r"
    fi
    local cmake=cmake
    (cd zstd-${ZSTD_VERSION}/build/cmake  \
        && $cmake . \
           -DCMAKE_BUILD_TYPE=Release \
           -DCMAKE_INSTALL_PREFIX:PATH=$BUILD_PREFIX \
           -DCMAKE_PREFIX_PATH=${BUILD_PREFIX} \
           -DCMAKE_OSX_ARCHITECTURES="${ARCH}" \
		   -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
	       -DCMAKE_OSX_DEPLOYMENT_TARGET=$MACOSX_DEPLOYMENT_TARGET \
	       -DCMAKE_OSX_ARCHITECTURES=$CMAKE_OSX_ARCHITECTURES \
           -DZSTD_LEGACY_SUPPORT=0 \
           -DSED_ERE_OPT=$sed_ere_opt \
        && $cmake --build . \
        && $cmake --install .)

    touch zstd-stamp
}


function build_pcre2 {
    if [ -e pcre-stamp ]; then return; fi
    wget https://github.com/PCRE2Project/pcre2/releases/download/pcre2-${PCRE_VERSION}/pcre2-${PCRE_VERSION}.tar.bz2
    tar -xjf "pcre2-${PCRE_VERSION}.tar.bz2"
    (cd pcre2-${PCRE_VERSION} \
        && ./configure --prefix=$BUILD_PREFIX \
        && make -j4 \
        && make install)
    touch pcre-stamp
}


function build_zlib {
    if [ -e zlib-stamp ]; then return; fi
    # Careful, this one may cause yum to segfault
    # Fossils directory should also contain latest
    # build_simple zlib $ZLIB_VERSION https://zlib.net/fossils
    wget https://www.zlib.net/zlib-$ZLIB_VERSION.tar.gz
    tar -xvf zlib-$ZLIB_VERSION.tar.gz
   (cd zlib-${ZLIB_VERSION} \
    && ./configure --prefix=$BUILD_PREFIX \
    && make \
    && make install)
    touch zlib-stamp
}


function build_jpeg {

    if [ -e jpeg-stamp ]; then return; fi
    wget http://ijg.org/files/jpegsrc.v${JPEG_VERSION}.tar.gz
    tar -xzf jpegsrc.v${JPEG_VERSION}.tar.gz
    (cd jpeg-${JPEG_VERSION} \
        && ./configure --prefix=$BUILD_PREFIX \
        && make \
        && make install)
    touch jpeg-stamp
}


 function build_giflib {
  if [ -e giflib-stamp ]; then return; fi
  GIFLIB_TAR="giflib-${GIFLIB_VERSION}.tar.gz"
  GIFLIB_URL="https://sourceforge.net/projects/giflib/files/giflib-${GIFLIB_VERSION}.tar.gz/download"
  wget -O "$GIFLIB_TAR" "$GIFLIB_URL"
  tar -xzf "$GIFLIB_TAR"
        (cd "giflib-${GIFLIB_VERSION}" \
        && make \
        && make install PREFIX=$BUILD_PREFIX)
        touch giflib-stamp
}


function build_libpng {

    if [ -e libpng-stamp ]; then return; fi

    build_zlib

    wget https://github.com/pnggroup/libpng/archive/refs/tags/v${LIBPNG_VERSION}.tar.gz -O libpng-${LIBPNG_VERSION}.tar.gz
    tar -xzf libpng-${LIBPNG_VERSION}.tar.gz
    (cd libpng-${LIBPNG_VERSION} \
        && ./configure --prefix=$BUILD_PREFIX \
        && make \
        && make install)
    touch libpng-stamp
}


function build_xz {
  if [ -e xz-stamp ]; then return; fi
  wget "https://tukaani.org/xz/xz-${XZ_VERSION}.tar.gz"
  tar -xzf "xz-${XZ_VERSION}.tar.gz"
  (cd "xz-${XZ_VERSION}" \
   && ./configure --prefix=$BUILD_PREFIX \
   && make \
   && make install)
   touch xz-stamp
}


function build_lcms2 {

  if [ -e lcms2-stamp ]; then return; fi

  build_tiff

  wget https://github.com/mm2/Little-CMS/releases/download/lcms${LCMS2_VERSION}/lcms2-${LCMS2_VERSION}.tar.gz
  tar -xzf lcms2-${LCMS2_VERSION}.tar.gz
  (cd lcms2-${LCMS2_VERSION} \
    && ./configure --prefix=$BUILD_PREFIX \
    && make -j$(nproc) \
    && make install)
  touch lcms2-stamp

}


function build_libdeflate {

   if [ -e libdeflate-stamp ]; then return; fi

   wget https://github.com/ebiggers/libdeflate/archive/refs/tags/v${LIBDEFLATE_VERSION}.tar.gz -O libdeflate-${LIBDEFLATE_VERSION}.tar.gz
   tar -xvzf libdeflate-${LIBDEFLATE_VERSION}.tar.gz
       local cmake=cmake
       (cd libdeflate-${LIBDEFLATE_VERSION} \
         && mkdir build && cd build \
         && $cmake .. \
        -DCMAKE_INSTALL_PREFIX:PATH=$BUILD_PREFIX \
        -DCMAKE_PREFIX_PATH=${BUILD_PREFIX} \
        -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
        -DCMAKE_OSX_DEPLOYMENT_TARGET=$MACOSX_DEPLOYMENT_TARGET \
        -DCMAKE_OSX_ARCHITECTURES=$CMAKE_OSX_ARCHITECTURES \
        -DBUILD_SHARED_LIBS=ON \
        -DCMAKE_BUILD_TYPE=Release \
        && $cmake --build . -j4 \
        && $cmake --install .)

   touch libdeflate-stamp
}


function build_libaec {
    if [ -e libaec-stamp ]; then return; fi
    LIBAEC_URL="https://github.com/MathisRosenhauer/libaec/releases/download/v${LIBAEC_VERSION}/libaec-${LIBAEC_VERSION}.tar.gz"
    wget "$LIBAEC_URL" -O libaec-${LIBAEC_VERSION}.tar.gz
    tar -xzf libaec-${LIBAEC_VERSION}.tar.gz
    (cd libaec-${LIBAEC_VERSION} \
        && ./configure --prefix=$BUILD_PREFIX \
        && make \
        && make install)
    touch libaec-stamp
}


function build_netcdf {

    if [ -e netcdf-stamp ]; then return; fi
    local cmake=cmake
    build_hdf5
    NETCDF_URL="https://github.com/Unidata/netcdf-c/archive/refs/tags/v${NETCDF_VERSION}.tar.gz"
    wget "$NETCDF_URL" -O "netcdf-c-${NETCDF_VERSION}.tar.gz"
    tar -xzf netcdf-c-${NETCDF_VERSION}.tar.gz
    (cd netcdf-c-${NETCDF_VERSION} \
        && mkdir build && cd build \
        && $cmake .. \
           -DCMAKE_BUILD_TYPE=Release \
           -DCMAKE_INSTALL_PREFIX:PATH=$BUILD_PREFIX \
           -DCMAKE_PREFIX_PATH=${BUILD_PREFIX} \
		   -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
	       -DCMAKE_OSX_DEPLOYMENT_TARGET=$MACOSX_DEPLOYMENT_TARGET \
	       -DCMAKE_OSX_ARCHITECTURES=$CMAKE_OSX_ARCHITECTURES \
		   -DENABLE_DAP=ON \
	       -DBUILD_SHARED_LIBS=ON \
        && $cmake --build . -j$(nproc) \
        && $cmake --install .)
    touch netcdf-stamp
}


function build_gdal {
    if [ -e gdal-stamp ]; then return; fi

    CFLAGS="$CFLAGS -DPROJ_RENAME_SYMBOLS"
    CXXFLAGS="$CXXFLAGS -DPROJ_RENAME_SYMBOLS -DPROJ_INTERNAL_CPP_NAMESPACE"

    build_blosc
    build_curl
    build_lerc
    build_jpeg
    build_libpng
    build_openjpeg
    build_jsonc
    build_sqlite
    build_proj
    build_expat
    build_geos
    build_hdf5
    build_netcdf
    build_zstd
    build_pcre2

    if [ -n "$IS_MACOS" ]; then
        GEOS_CONFIG="-DGDAL_USE_GEOS=OFF"
    else
        GEOS_CONFIG="-DGDAL_USE_GEOS=ON"
    fi

    # To use GDAL 3.10.3 with PDF: Fix build against Poppler 2025.05.0
    # wget https://github.com/OSGeo/gdal/archive/refs/heads/release/3.10.zip
    # 7z x 3.10.zip
    # mv gdal-release-3.10 gdal-3.10.3

    wget https://download.osgeo.org/gdal/${GDAL_VERSION}/gdal-${GDAL_VERSION}.tar.gz
    tar -xzf gdal-${GDAL_VERSION}.tar.gz

    local cmake=cmake
    (cd gdal-${GDAL_VERSION} \
        && mkdir build \
        && cd build \
        && $cmake .. \
        -DCMAKE_INSTALL_PREFIX=$BUILD_PREFIX \
        -DCMAKE_PREFIX_PATH=${BUILD_PREFIX} \
        -DCMAKE_INCLUDE_PATH=$BUILD_PREFIX/include \
        -DCMAKE_LIBRARY_PATH=$BUILD_PREFIX/lib \
        -DCMAKE_PROGRAM_PATH=$BUILD_PREFIX/bin \
        -DCMAKE_OSX_DEPLOYMENT_TARGET=$MACOSX_DEPLOYMENT_TARGET \
        -DCMAKE_OSX_ARCHITECTURES=$CMAKE_OSX_ARCHITECTURES \
        -DBUILD_SHARED_LIBS=ON \
        -DCMAKE_BUILD_TYPE=Release \
        -DGDAL_BUILD_OPTIONAL_DRIVERS=ON \
        -DOGR_BUILD_OPTIONAL_DRIVERS=OFF \
        -DSQLite3_INCLUDE_DIR=$BUILD_PREFIX/include \
        -DSQLite3_LIBRARY=$BUILD_PREFIX/lib/libsqlite3.$lib_ext \
        ${GEOS_CONFIG} \
        -DGDAL_USE_CURL=ON \
        -DGDAL_USE_TIFF=ON \
        -DGDAL_USE_TIFF_INTERNAL=OFF \
        -DGDAL_USE_GEOTIFF_INTERNAL=ON \
        -DGDAL_ENABLE_DRIVER_GIF=ON \
        -DGDAL_ENABLE_DRIVER_GRIB=ON \
        -DGDAL_ENABLE_DRIVER_JPEG=ON \
        -DGDAL_USE_JXL=OFF \
        -DGDAL_USE_ICONV=ON \
        -DGDAL_USE_JSONC=ON \
        -DGDAL_USE_JSONC_INTERNAL=OFF \
        -DGDAL_USE_ZLIB=ON \
        -DGDAL_USE_ZLIB_INTERNAL=OFF \
        -DGDAL_ENABLE_DRIVER_HDF5=ON \
        -DGDAL_USE_HDF5=ON \
        -DHDF5_INCLUDE_DIRS=$BUILD_PREFIX/include \
        -DGDAL_ENABLE_DRIVER_NETCDF=ON \
        -DGDAL_USE_NETCDF=ON \
        -DGDAL_ENABLE_DRIVER_OPENJPEG=ON \
        -DGDAL_ENABLE_DRIVER_PNG=ON \
        -DGDAL_ENABLE_DRIVER_OGCAPI=OFF \
        -DGDAL_USE_SQLITE3=ON \
        -DOGR_ENABLE_DRIVER_SQLITE=ON \
        -DOGR_ENABLE_DRIVER_GPKG=ON \
        -DOGR_ENABLE_DRIVER_MVT=ON \
        -DGDAL_ENABLE_DRIVER_MBTILES=ON \
        -DOGR_ENABLE_DRIVER_OSM=ON \
        -DBUILD_PYTHON_BINDINGS=OFF \
        -DBUILD_JAVA_BINDINGS=OFF \
        -DBUILD_CSHARP_BINDINGS=OFF \
        -DGDAL_USE_SFCGAL=OFF \
        -DGDAL_USE_XERCESC=OFF \
        -DGDAL_USE_LIBXML2=OFF \
        -DGDAL_USE_PCRE2=ON \
        -DPCRE2_INCLUDE_DIR=$BUILD_PREFIX/include \
        -DPCRE2-8_LIBRARY=$BUILD_PREFIX/lib/libpcre2-8.$lib_ext \
        -DGDAL_USE_POSTGRESQL=OFF \
        -DGDAL_ENABLE_POSTGISRASTER=OFF \
        -DGDAL_USE_OPENEXR=OFF \
        -DGDAL_ENABLE_EXR=OFF \
        -DGDAL_USE_OPENEXR=OFF \
        -DGDAL_USE_HEIF=OFF \
        -DGDAL_ENABLE_HEIF=OFF \
        -DGDAL_USE_ODBC=OFF \
        -DOGR_ENABLE_DRIVER_AVC=ON \
        -DGDAL_ENABLE_DRIVER_AIGRID=ON \
        -DGDAL_ENABLE_DRIVER_AAIGRID=ON \
        -DGDAL_USE_LERC=ON \
        -DGDAL_USE_LERC_INTERNAL=OFF \
        -DGDAL_USE_PCRE2=OFF \
        -DGDAL_USE_POSTGRESQL=OFF \
        -DGDAL_USE_ODBC=OFF \
        && $cmake --build . -j4 \
        && $cmake --install .)
    if [ -n "$IS_MACOS" ]; then
        :
    else
        strip -v --strip-unneeded ${BUILD_PREFIX}/lib/libgdal.so.* || true
        strip -v --strip-unneeded ${BUILD_PREFIX}/lib64/libgdal.so.* || true
    fi
    touch gdal-stamp
}

    suppress update_env_for_build_prefix
    build_zlib
    suppress build_xz
    suppress build_nghttp2
    # Remove previously installed curl.
    rm -rf $BUILD_PREFIX/lib/libcurl* || true
	suppress build_curl
    build_libwebp
    build_zstd
	build_libdeflate
    build_jpeg
    build_lerc
    build_tiff
    build_openjpeg
    suppress build_jsonc
    build_sqlite
    build_proj
    suppress build_expat
    suppress build_geos
    suppress build_hdf5
    suppress build_netcdf
    build_gdal

echo "List contents of $BUILD_PREFIX/lib directory"
ls "$BUILD_PREFIX/lib"

echo " "

if [ -d "$BUILD_PREFIX/lib64" ]; then
  echo "List contents of $BUILD_PREFIX/lib64 directory"
  ls "$BUILD_PREFIX/lib64"
fi

echo "Using GDAL_CONFIG at: $GDAL_CONFIG"

# Run the gdal-config binary
"$GDAL_CONFIG" --version

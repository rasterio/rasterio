PROJ_VERSION=9.7.1
SQLITE_VERSION=3510100
OPENSSL_VERSION=3.6.0
CURL_VERSION=8.17.0
ZLIB_VERSION=1.3.1
TIFF_VERSION=4.7.1
NGHTTP2_VERSION=1.65.0
LERC_VERSION=4.0.0
JPEG_VERSION=9f
LIBWEBP_VERSION=1.6.0
ZSTD_VERSION=1.5.7
LIBPNG_VERSION=1.6.53
OPENJPEG_VERSION=2.5.4
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
macos-arm64) TARGET="darwin64-${CMAKE_OSX_ARCHITECTURES}-cc" ;;
macos-x86_64) TARGET="darwin64-x86_64-cc" ;;
linux-aarch64) TARGET="linux-aarch64" ;;
linux-x86_64) TARGET="linux-x86_64" ;;
*)
	echo "❌ Unsupported platform: $PLATFORM"
	exit 1
	;;
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
	(
		if [[ -n $errexit_set ]]; then set -e; fi
		"$@" >"$tmp" 2>&1
	)
	ret=$?
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

function fetch_untar() {
    opts="--retry-connrefused \
          --waitretry=30 \
          --dns-timeout=20 \
          --connect-timeout=20 \
          --read-timeout=300 \
          --timeout=300 \
          -t 4"

    if [[ "$#" -eq 1 ]]; then
        # Only URL
        wget $opts "$1"

    elif [[ "$#" -eq 2 ]]; then
        # URL + TAR_FILE (show hash, no check)
        wget $opts "$1"
        TAR_FILE="$2"
        echo "SHA256: "
        sha256sum "$TAR_FILE"
        if [[ $TAR_FILE == *.gz ]]; then
            tar -xzf "$TAR_FILE"
        elif [[ $TAR_FILE == *.bz2 ]]; then
            tar -xjf "$TAR_FILE"
        else
            echo "Unsupported file type: $TAR_FILE"
        fi

    elif [[ "$#" -eq 3 && "$2" == "-O" ]]; then
        # URL + -O new-name (rename, show hash, no check)
        wget $opts "$1" -O "$3"
        TAR_FILE="$3"
        echo "SHA256: "
        sha256sum "$TAR_FILE"
        if [[ $TAR_FILE == *.gz ]]; then
            tar -xzf "$TAR_FILE"
        elif [[ $TAR_FILE == *.bz2 ]]; then
            tar -xjf "$TAR_FILE"
        else
            echo "Unsupported file type: $TAR_FILE"
        fi

    elif [[ "$#" -eq 3 ]]; then
        # URL + TAR_FILE + SHA_FILE_URL (hash check, no rename)
        wget $opts "$1"
        TAR_FILE="$2"
        SHA256="$3"    
        EXPECTED_HASH="$SHA256"
        ACTUAL_HASH=$(sha256sum "$TAR_FILE" | cut -d ' ' -f1)

        echo "Expected hash: $EXPECTED_HASH"
        echo "Actual hash: $ACTUAL_HASH"

        if [ "$EXPECTED_HASH" == "$ACTUAL_HASH" ]; then
            echo "SHA256 hash verified. Extracting..."
            if [[ $TAR_FILE == *.gz ]]; then
                tar -xzf "$TAR_FILE"
            elif [[ $TAR_FILE == *.bz2 ]]; then
                tar -xjf "$TAR_FILE"
            else
                echo "Unsupported file type: $TAR_FILE"
            fi
        else
            echo "Hash mismatch! Aborting."
            exit 1
        fi

    elif [[ "$#" -eq 4 && "$2" == "-O" ]]; then
        # URL + -O new-name + SHA_FILE_URL (rename + hash check)
        wget $opts "$1" -O "$3"
        TAR_FILE="$3"
        SHA256="$4"    
        EXPECTED_HASH="$SHA256"
        ACTUAL_HASH=$(sha256sum "$TAR_FILE" | cut -d ' ' -f1)

        echo "Expected hash: $EXPECTED_HASH"
        echo "Actual hash: $ACTUAL_HASH"

        if [ "$EXPECTED_HASH" == "$ACTUAL_HASH" ]; then
            echo "SHA256 hash verified. Extracting..."
            if [[ $TAR_FILE == *.gz ]]; then
                tar -xzf "$TAR_FILE"
            elif [[ $TAR_FILE == *.bz2 ]]; then
                tar -xjf "$TAR_FILE"
            else
                echo "Unsupported file type: $TAR_FILE"
            fi
        else
            echo "Hash mismatch! Aborting."
            exit 1
        fi
    fi
}


echo "Downloading source code..."
 
### Avoid simultaneous downloads

if [ "$ARCH" = "x86_64" ]; then
	echo "Architecture is x86_64. Waiting 60 seconds..."
	sleep 60
fi

if [ "$OS" = "linux" ]; then
	echo "OS is linux. Waiting 30 seconds..."
	sleep 30
fi


BLOSC_URL="https://github.com/Blosc/c-blosc/archive/refs/tags/v${BLOSC_VERSION}.tar.gz"
BLOSC_FNAME="c-blosc-${BLOSC_VERSION}"
fetch_untar ${BLOSC_URL} -O ${BLOSC_FNAME}.tar.gz

CURL_URL="https://curl.se/download/curl-${CURL_VERSION}.tar.gz"
CURL_FNAME="curl-${CURL_VERSION}"
CURL_SHA256="e8e74cdeefe5fb78b3ae6e90cd542babf788fa9480029cfcee6fd9ced42b7910"
fetch_untar ${CURL_URL} ${CURL_FNAME}.tar.gz ${CURL_SHA256}

if [ -n "$IS_MACOS" ]; then
	:
else
	EXPAT_VERSION_UNDERSCORED="${EXPAT_VERSION//./_}"
	EXPAT_URL="https://github.com/libexpat/libexpat/releases/download/R_${EXPAT_VERSION_UNDERSCORED}/expat-${EXPAT_VERSION}.tar.bz2"
	EXPAT_FNAME="expat-${EXPAT_VERSION}"
	fetch_untar ${EXPAT_URL} ${EXPAT_FNAME}.tar.bz2
fi

GDAL_URL="https://download.osgeo.org/gdal/${GDAL_VERSION}/gdal-${GDAL_VERSION}.tar.gz"
GDAL_FNAME="gdal-${GDAL_VERSION}"
GDAL_SHA256="266cbadf8534d1de831db8834374afd95603e0a6af4f53d0547ae0d46bd3d2d1"
fetch_untar ${GDAL_URL} ${GDAL_FNAME}.tar.gz ${GDAL_SHA256}

GIFLIB_URL="https://sourceforge.net/projects/giflib/files/giflib-${GIFLIB_VERSION}.tar.gz/download"
GIFLIB_FNAME="giflib-${GIFLIB_VERSION}"
fetch_untar $GIFLIB_URL -O ${GIFLIB_FNAME}.tar.gz

GEOS_URL="http://download.osgeo.org/geos/geos-${GEOS_VERSION}.tar.bz2"
GEOS_FNAME="geos-${GEOS_VERSION}"
fetch_untar ${GEOS_URL} ${GEOS_FNAME}.tar.bz2

HDF5_VERSION_UNDERSCORED="${HDF5_VERSION//./_}"; HDF5_VERSION_SHORT="${HDF5_VERSION_UNDERSCORED%_*}"
HDF5_URL="https://support.hdfgroup.org/releases/hdf5/v${HDF5_VERSION_SHORT}/v${HDF5_VERSION_UNDERSCORED}/downloads/hdf5-${HDF5_VERSION}.tar.gz"
HDF5_FNAME="hdf5-${HDF5_VERSION}"
HDF5_SHA256="e4defbac30f50d64e1556374aa49e574417c9e72c6b1de7a4ff88c4b1bea6e9b"
fetch_untar ${HDF5_URL} ${HDF5_FNAME}.tar.gz ${HDF5_SHA256}

JPEG_URL="http://ijg.org/files/jpegsrc.v${JPEG_VERSION}.tar.gz"
JPEG_FNAME="jpeg-${JPEG_VERSION}"
fetch_untar $JPEG_URL -O ${JPEG_FNAME}.tar.gz

JSONC_URL="https://s3.amazonaws.com/json-c_releases/releases/json-c-${JSONC_VERSION}.tar.gz"
JSONC_FNAME="json-c-${JSONC_VERSION}"
fetch_untar ${JSONC_URL} ${JSONC_FNAME}.tar.gz

LCMS2_URL="https://github.com/mm2/Little-CMS/releases/download/lcms${LCMS2_VERSION}/lcms2-${LCMS2_VERSION}.tar.gz"
LCMS2_FNAME="lcms2-${LCMS2_VERSION}"
fetch_untar ${LCMS2_URL} ${LCMS2_FNAME}.tar.gz

LERC_URL="https://github.com/Esri/lerc/archive/refs/tags/v${LERC_VERSION}.tar.gz"
LERC_FNAME="lerc-${LERC_VERSION}"
fetch_untar ${LERC_URL} -O ${LERC_FNAME}.tar.gz

LIBAEC_URL="https://github.com/MathisRosenhauer/libaec/releases/download/v${LIBAEC_VERSION}/libaec-${LIBAEC_VERSION}.tar.gz"
LIBAEC_FNAME="libaec-${LIBAEC_VERSION}"
fetch_untar ${LIBAEC_URL} -O ${LIBAEC_FNAME}.tar.gz

LIBDEFLATE_URL="https://github.com/ebiggers/libdeflate/archive/refs/tags/v${LIBDEFLATE_VERSION}.tar.gz"
LIBDEFLATE_FNAME="libdeflate-${LIBDEFLATE_VERSION}"
fetch_untar ${LIBDEFLATE_URL} -O ${LIBDEFLATE_FNAME}.tar.gz

LIBPNG_URL="https://github.com/pnggroup/libpng/archive/refs/tags/v${LIBPNG_VERSION}.tar.gz"
LIBPNG_FNAME="libpng-${LIBPNG_VERSION}"
fetch_untar ${LIBPNG_URL} -O ${LIBPNG_FNAME}.tar.gz

LIBWEBP_URL="https://github.com/webmproject/libwebp/archive/refs/tags/v$LIBWEBP_VERSION.tar.gz"
LIBWEBP_FNAME="libwebp-${LIBWEBP_VERSION}"
fetch_untar ${LIBWEBP_URL} -O ${LIBWEBP_FNAME}.tar.gz

NETCDF_URL="https://github.com/Unidata/netcdf-c/archive/refs/tags/v${NETCDF_VERSION}.tar.gz"
NETCDF_FNAME="netcdf-c-${NETCDF_VERSION}"
fetch_untar ${NETCDF_URL} -O ${NETCDF_FNAME}.tar.gz

NGHTTP2_URL="https://github.com/nghttp2/nghttp2/releases/download/v${NGHTTP2_VERSION}/nghttp2-${NGHTTP2_VERSION}.tar.gz"
NGHTTP2_FNAME="nghttp2-${NGHTTP2_VERSION}"
fetch_untar ${NGHTTP2_URL} ${NGHTTP2_FNAME}.tar.gz

OPENJPEG_URL="https://github.com/uclouvain/openjpeg/archive/refs/tags/v${OPENJPEG_VERSION}.tar.gz"
OPENJPEG_FNAME="openjpeg-${OPENJPEG_VERSION}"
fetch_untar ${OPENJPEG_URL} -O ${OPENJPEG_FNAME}.tar.gz

OPENSSL_URL="https://github.com/openssl/openssl/releases/download/openssl-$OPENSSL_VERSION/openssl-$OPENSSL_VERSION.tar.gz"
OPENSSL_FNAME="openssl-${OPENSSL_VERSION}"
OPENSSL_SHA256="b6a5f44b7eb69e3fa35dbf15524405b44837a481d43d81daddde3ff21fcbb8e9"
fetch_untar ${OPENSSL_URL} ${OPENSSL_FNAME}.tar.gz ${OPENSSL_SHA256}

PCRE2_URL="https://github.com/PCRE2Project/pcre2/releases/download/pcre2-${PCRE_VERSION}/pcre2-${PCRE_VERSION}.tar.bz2"
PCRE2_FNAME="pcre2-${PCRE_VERSION}"
fetch_untar $PCRE2_URL ${PCRE2_FNAME}.tar.bz2

PROJ_URL="https://download.osgeo.org/proj/proj-${PROJ_VERSION}.tar.gz"
PROJ_FNAME="proj-${PROJ_VERSION}"
fetch_untar ${PROJ_URL} ${PROJ_FNAME}.tar.gz

SQLITE_URL="https://www.sqlite.org/2025/sqlite-autoconf-${SQLITE_VERSION}.tar.gz"
SQLITE_FNAME="sqlite-autoconf-${SQLITE_VERSION}"
fetch_untar ${SQLITE_URL} ${SQLITE_FNAME}.tar.gz

TIFF_URL="https://download.osgeo.org/libtiff/tiff-${TIFF_VERSION}.tar.gz"
TIFF_FNAME="tiff-${TIFF_VERSION}"
fetch_untar ${TIFF_URL} ${TIFF_FNAME}.tar.gz

XZ_URL="https://tukaani.org/xz/xz-${XZ_VERSION}.tar.gz"
XZ_FNAME="xz-${XZ_VERSION}"
fetch_untar ${XZ_URL} ${XZ_FNAME}.tar.gz

ZLIB_URL="https://www.zlib.net/zlib-$ZLIB_VERSION.tar.gz"
ZLIB_FNAME="zlib-${ZLIB_VERSION}"
ZLIB_SHA256="9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23"
fetch_untar $ZLIB_URL ${ZLIB_FNAME}.tar.gz ${ZLIB_SHA256}

ZSTD_URL="https://github.com/facebook/zstd/archive/v${ZSTD_VERSION}.tar.gz"
ZSTD_FNAME="zstd-${ZSTD_VERSION}"
fetch_untar ${ZSTD_URL} -O ${ZSTD_FNAME}.tar.gz


echo "Compiling libraries ..."

function build_hdf5 {
	if [ -e hdf5-stamp ]; then return; fi
	build_zlib
	# libaec is a drop-in replacement for szip
	build_libaec

	(cd ${HDF5_FNAME} &&
		export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$BUILD_PREFIX/lib &&
		export DYLD_LIBRARY_PATH=$DYLD_LIBRARY_PATH:$BUILD_PREFIX/lib &&
		./configure --with-szlib=$BUILD_PREFIX --prefix=$BUILD_PREFIX \
			--enable-threadsafe --enable-unsupported --with-pthread=yes &&
		make -j4 &&
		make install)
	touch hdf5-stamp
}

function build_blosc {
	if [ -e blosc-stamp ]; then return; fi
	local cmake=cmake

	(cd ${BLOSC_FNAME} &&
		$cmake -DCMAKE_INSTALL_PREFIX=$BUILD_PREFIX -DCMAKE_POLICY_VERSION_MINIMUM=3.5 . &&
		make install)
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

	(cd ${GEOS_FNAME} &&
		mkdir build && cd build &&
		$cmake .. \
			-DCMAKE_INSTALL_PREFIX:PATH=$BUILD_PREFIX \
			-DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
			-DCMAKE_OSX_DEPLOYMENT_TARGET=$MACOSX_DEPLOYMENT_TARGET \
			-DCMAKE_OSX_ARCHITECTURES=$CMAKE_OSX_ARCHITECTURES \
			-DBUILD_SHARED_LIBS=ON \
			-DCMAKE_BUILD_TYPE=Release \
			-DENABLE_IPO=ON \
			-DBUILD_APPS:BOOL=OFF \
			-DBUILD_TESTING:BOOL=OFF &&
		$cmake --build . -j4 &&
		$cmake --install .)
	touch geos-stamp
}

function build_jsonc {
	if [ -e jsonc-stamp ]; then return; fi
	local cmake=cmake

	(cd ${JSONC_FNAME} &&
		$cmake -DCMAKE_INSTALL_PREFIX=$BUILD_PREFIX -DCMAKE_OSX_DEPLOYMENT_TARGET=$MACOSX_DEPLOYMENT_TARGET -DCMAKE_POLICY_VERSION_MINIMUM=3.5 . &&
		make -j4 &&
		make install)
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

	local cmake=cmake
	(cd ${PROJ_FNAME} &&
		$cmake . \
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
			-DBUILD_TESTING:BOOL=OFF &&
		$cmake --build . -j$(nproc) &&
		$cmake --install .)
	touch proj-stamp
}

function build_sqlite {

	if [ -z "$IS_MACOS" ]; then
		CFLAGS="$CFLAGS -DHAVE_PREAD64 -DHAVE_PWRITE64"
	fi

	if [ -e sqlite-stamp ]; then return; fi

	(cd ${SQLITE_FNAME} &&
		./configure --enable-rtree --enable-threadsafe --prefix=$BUILD_PREFIX &&
		make &&
		make install)
	touch sqlite-stamp
}

function build_expat {
	if [ -e expat-stamp ]; then return; fi
	if [ -n "$IS_MACOS" ]; then
		:
	else

		(cd ${EXPAT_FNAME} &&
			./configure --prefix=$BUILD_PREFIX &&
			make -j4 &&
			make install)
	fi
	touch expat-stamp
}

function build_lerc {

	if [ -e lerc-stamp ]; then return; fi
	local cmake=cmake

	(cd ${LERC_FNAME} &&
		mkdir cmake_build && cd cmake_build &&
		$cmake .. \
			-DCMAKE_INSTALL_PREFIX=$BUILD_PREFIX \
			-DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
			-DCMAKE_OSX_DEPLOYMENT_TARGET=$MACOSX_DEPLOYMENT_TARGET \
			-DCMAKE_OSX_ARCHITECTURES=$CMAKE_OSX_ARCHITECTURES \
			-DBUILD_SHARED_LIBS=ON \
			-DCMAKE_BUILD_TYPE=Release \
			-DENABLE_IPO=ON &&
		$cmake --build . -j4 &&
		$cmake --install .)
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

	(cd ${TIFF_FNAME} &&
		./configure --prefix=$BUILD_PREFIX --libdir=$BUILD_PREFIX/lib --enable-zstd --enable-webp --enable-lerc --with-jpeg-include-dir=$BUILD_PREFIX/include --with-jpeg-lib-dir=$BUILD_PREFIX/lib &&
		make -j4 &&
		make install)
	touch tiff-stamp
}

function build_openjpeg {

	if [ -e openjpeg-stamp ]; then return; fi

	build_zlib
	build_tiff
	build_lcms2

	local cmake=cmake
	(cd ${OPENJPEG_FNAME} &&
		mkdir build &&
		cd build &&
		$cmake .. \
			-DCMAKE_BUILD_TYPE=Release \
			-DCMAKE_INSTALL_PREFIX=$BUILD_PREFIX \
			-DCMAKE_PREFIX_PATH=${BUILD_PREFIX} \
			-DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
			-DCMAKE_OSX_DEPLOYMENT_TARGET=$MACOSX_DEPLOYMENT_TARGET \
			-DCMAKE_OSX_ARCHITECTURES=$CMAKE_OSX_ARCHITECTURES &&
		$cmake --build . -j$(nproc) &&
		$cmake --install .)

	touch openjpeg-stamp
}

function build_libwebp {

	build_libpng
	build_giflib

	if [ -e libwebp-stamp ]; then return; fi

	(cd ${LIBWEBP_FNAME} &&
		./autogen.sh &&
		./configure --prefix=$BUILD_PREFIX \
			--enable-libwebpmux \
			--enable-libwebpdemux &&
		make &&
		make install)
	touch libwebp-stamp
}

function build_nghttp2 {
	if [ -e nghttp2-stamp ]; then return; fi

	(cd ${NGHTTP2_FNAME} &&
		./configure --enable-lib-only --prefix=$BUILD_PREFIX &&
		make -j4 &&
		make install)
	touch nghttp2-stamp
}

function build_openssl  {
	if [ -e openssl-stamp ]; then return; fi

	(cd ${OPENSSL_FNAME} &&
		./config $TARGET -fPIC --prefix=$BUILD_PREFIX &&
		make -j4 &&
		make install)
	touch openssl-stamp
}

function build_curl {
	if [ -e curl-stamp ]; then return; fi

	suppress build_openssl
	build_nghttp2
	local flags="--prefix=$BUILD_PREFIX --with-nghttp2=$BUILD_PREFIX --with-zlib=$BUILD_PREFIX --with-ssl=$BUILD_PREFIX --enable-shared --without-libidn2 --without-libpsl"

	(cd ${CURL_FNAME} &&
		LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$BUILD_PREFIX/lib:$BUILD_PREFIX/lib64 &&
		DYLD_LIBRARY_PATH=$DYLD_LIBRARY_PATH:$BUILD_PREFIX/lib ./configure $flags &&
		make -j4 &&
		if [ -n "$IS_MACOS" ]; then make install; else make install; fi)
	touch curl-stamp
}

function build_zstd {

	if [ -e zstd-stamp ]; then return; fi

	if [ -n "$IS_MACOS" ]; then
		sed_ere_opt="-E"
	else
		sed_ere_opt="-r"
	fi
	local cmake=cmake
	(cd ${ZSTD_FNAME}/build/cmake &&
		$cmake . \
			-DCMAKE_BUILD_TYPE=Release \
			-DCMAKE_INSTALL_PREFIX:PATH=$BUILD_PREFIX \
			-DCMAKE_PREFIX_PATH=${BUILD_PREFIX} \
			-DCMAKE_OSX_ARCHITECTURES="${ARCH}" \
			-DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
			-DCMAKE_OSX_DEPLOYMENT_TARGET=$MACOSX_DEPLOYMENT_TARGET \
			-DCMAKE_OSX_ARCHITECTURES=$CMAKE_OSX_ARCHITECTURES \
			-DZSTD_LEGACY_SUPPORT=0 \
			-DSED_ERE_OPT=$sed_ere_opt &&
		$cmake --build . &&
		$cmake --install .)

	touch zstd-stamp
}

function build_pcre2 {
	if [ -e pcre-stamp ]; then return; fi

	(cd ${PCRE2_FNAME} &&
		./configure --prefix=$BUILD_PREFIX &&
		make -j4 &&
		make install)
	touch pcre-stamp
}

function build_zlib {
	if [ -e zlib-stamp ]; then return; fi

	(cd ${ZLIB_FNAME} &&
		./configure --prefix=$BUILD_PREFIX &&
		make &&
		make install)
	touch zlib-stamp
}

function build_jpeg {

	if [ -e jpeg-stamp ]; then return; fi

	(cd ${JPEG_FNAME} &&
		./configure --prefix=$BUILD_PREFIX &&
		make &&
		make install)
	touch jpeg-stamp
}

function build_giflib {
	if [ -e giflib-stamp ]; then return; fi

	(cd ${GIFLIB_FNAME} &&
		make &&
		make install PREFIX=$BUILD_PREFIX)
	touch giflib-stamp
}

function build_libpng {

	if [ -e libpng-stamp ]; then return; fi

	build_zlib

	(cd ${LIBPNG_FNAME} &&
		./configure --prefix=$BUILD_PREFIX &&
		make &&
		make install)
	touch libpng-stamp
}

function build_xz {
	if [ -e xz-stamp ]; then return; fi

	(cd ${XZ_FNAME} &&
		./configure --prefix=$BUILD_PREFIX &&
		make &&
		make install)
	touch xz-stamp
}

function build_lcms2 {

	if [ -e lcms2-stamp ]; then return; fi

	build_tiff

	(cd ${LCMS2_FNAME} &&
		./configure --prefix=$BUILD_PREFIX &&
		make -j$(nproc) &&
		make install)
	touch lcms2-stamp

}

function build_libdeflate {

	if [ -e libdeflate-stamp ]; then return; fi

	local cmake=cmake
	(cd ${LIBDEFLATE_FNAME} &&
		mkdir build && cd build &&
		$cmake .. \
			-DCMAKE_INSTALL_PREFIX:PATH=$BUILD_PREFIX \
			-DCMAKE_PREFIX_PATH=${BUILD_PREFIX} \
			-DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
			-DCMAKE_OSX_DEPLOYMENT_TARGET=$MACOSX_DEPLOYMENT_TARGET \
			-DCMAKE_OSX_ARCHITECTURES=$CMAKE_OSX_ARCHITECTURES \
			-DBUILD_SHARED_LIBS=ON \
			-DCMAKE_BUILD_TYPE=Release &&
		$cmake --build . -j4 &&
		$cmake --install .)

	touch libdeflate-stamp
}

function build_libaec {
	if [ -e libaec-stamp ]; then return; fi

	(cd ${LIBAEC_FNAME} &&
		./configure --prefix=$BUILD_PREFIX &&
		make &&
		make install)
	touch libaec-stamp
}

function build_netcdf {

	if [ -e netcdf-stamp ]; then return; fi
	local cmake=cmake
	build_hdf5

	(cd ${NETCDF_FNAME} &&
		mkdir build && cd build &&
		$cmake .. \
			-DCMAKE_BUILD_TYPE=Release \
			-DCMAKE_INSTALL_PREFIX:PATH=$BUILD_PREFIX \
			-DCMAKE_PREFIX_PATH=${BUILD_PREFIX} \
			-DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
			-DCMAKE_OSX_DEPLOYMENT_TARGET=$MACOSX_DEPLOYMENT_TARGET \
			-DCMAKE_OSX_ARCHITECTURES=$CMAKE_OSX_ARCHITECTURES \
			-DENABLE_DAP=ON \
			-DBUILD_SHARED_LIBS=ON &&
		$cmake --build . -j$(nproc) &&
		$cmake --install .)
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

	local cmake=cmake
	(cd ${GDAL_FNAME} &&
		mkdir build &&
		cd build &&
		$cmake .. \
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
			-DGDAL_USE_POSTGRESQL=OFF \
			-DGDAL_USE_ODBC=OFF &&
		$cmake --build . -j4 &&
		$cmake --install .)
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

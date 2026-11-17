"""Add a PEP 770 SBOM of the bundled native libraries to rasterio wheels.

Usage: GDAL_VERSION=x.y.z python ci/sbom.py WHEELHOUSE

auditwheel (Linux) and delocate (macOS) copy the libraries built by
ci/config.sh into the wheel without saying what they are. This writes a
CycloneDX document to rasterio-<version>.dist-info/sboms/rasterio.cdx.json
naming each library with the version pinned in ci/config.sh, and fails if a
bundled library has no entry in COMPONENTS or no pin.
"""

import base64
import hashlib
import json
import os
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# name: (NAME_VERSION pin in ci/config.sh, CPE vendor:product or None, library stems)
COMPONENTS = {
    "gdal": ("GDAL", "osgeo:gdal", ["gdal"]),
    "proj": ("PROJ", None, ["proj"]),
    "sqlite": ("SQLITE", "sqlite:sqlite", ["sqlite3"]),
    "openssl": ("OPENSSL", "openssl:openssl", ["ssl", "crypto"]),
    "curl": ("CURL", "haxx:curl", ["curl"]),
    "nghttp2": ("NGHTTP2", "nghttp2:nghttp2", ["nghttp2"]),
    "libtiff": ("TIFF", "libtiff:libtiff", ["tiff"]),
    "lerc": ("LERC", None, ["Lerc"]),
    "libwebp": ("LIBWEBP", "webmproject:libwebp", ["webp", "sharpyuv"]),
    "zstd": ("ZSTD", "facebook:zstandard", ["zstd"]),
    "libpng": ("LIBPNG", "libpng:libpng", ["png16"]),
    "openjpeg": ("OPENJPEG", "uclouvain:openjpeg", ["openjp2"]),
    "giflib": ("GIFLIB", "giflib_project:giflib", ["gif"]),
    "json-c": ("JSONC", "json-c:json-c", ["json-c"]),
    "xz": ("XZ", "tukaani:xz", ["lzma"]),
    "hdf5": ("HDF5", "hdfgroup:hdf5", ["hdf5", "hdf5_hl"]),
    "libaec": ("LIBAEC", None, ["aec", "sz"]),
    "netcdf-c": ("NETCDF", "unidata:netcdf", ["netcdf"]),
    "geos": ("GEOS", None, ["geos", "geos_c"]),
    "c-blosc": ("BLOSC", None, ["blosc"]),
    "pcre2": ("PCRE", "pcre:pcre2", ["pcre2-8"]),
    "libdeflate": ("LIBDEFLATE", None, ["deflate"]),
    "libjpeg-turbo": ("JPEGTURBO", "libjpeg-turbo:libjpeg-turbo", ["jpeg"]),
    "zlib": ("ZLIB", "zlib:zlib", ["z"]),
}
STEMS = {stem: name for name, (_, _, stems) in COMPONENTS.items() for stem in stems}
# rasterio.libs/libgdal-77dd9dd6.so.38.3.12.4 (auditwheel)
# rasterio/.dylibs/libgdal.38.3.12.4.dylib (delocate)
LIBRARY = re.compile(r"lib(.+?)(?:-[0-9a-f]{8})?(?:\.\d+)*\.(?:so|dylib)[.\d]*")


def read_pins():
    config = (Path(__file__).parent / "config.sh").read_text()
    pins = dict(re.findall(r"^(\w+)_VERSION=(\S+)$", config, re.M))
    pins["GDAL"] = os.environ.get("GDAL_VERSION")
    sqlite = pins.get("SQLITE", "")  # 3530100 is 3.53.1
    if sqlite.isdigit():
        parts = [sqlite[:-6], sqlite[-6:-4], sqlite[-4:-2], sqlite[-2:]]
        pins["SQLITE"] = ".".join(str(int(p)) for p in parts).removesuffix(".0")
    return pins


def add_sbom(wheel, pins):
    with zipfile.ZipFile(wheel) as zf:
        names = zf.namelist()
    record = next(n for n in names if re.fullmatch(r"[^/]+\.dist-info/RECORD", n))
    dist_info = record.split("/")[0]
    version = dist_info.removeprefix("rasterio-").removesuffix(".dist-info")

    found, errors = {}, []
    for path in names:
        folder, _, filename = path.rpartition("/")
        if folder not in ("rasterio.libs", "rasterio/.dylibs") or not filename:
            continue
        m = LIBRARY.fullmatch(filename)
        name = STEMS.get(m.group(1)) if m else None
        if name is None:
            errors.append(f"{path}: unknown library, add it to ci/sbom.py")
        elif not pins.get(COMPONENTS[name][0]):
            errors.append(f"{path}: no {COMPONENTS[name][0]}_VERSION pin for {name}")
        else:
            found.setdefault(name, []).append(path)
    if errors or not found:
        errors = errors or ["no bundled libraries found"]
        sys.exit(f"{wheel.name}: cannot write SBOM\n  " + "\n  ".join(errors))

    root = f"pkg:pypi/rasterio@{version}"
    components = []
    for name in sorted(found):
        pin, cpe, _ = COMPONENTS[name]
        v = pins[pin]
        purl = f"pkg:generic/{name}@{v}"
        component = {
            "type": "library",
            "bom-ref": purl,
            "name": name,
            "version": v,
            "purl": purl,
        }
        if cpe:
            component["cpe"] = f"cpe:2.3:a:{cpe}:{v}:*:*:*:*:*:*:*"
        component["evidence"] = {"occurrences": [{"location": p} for p in found[name]]}
        components.append(component)
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "metadata": {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tools": {"components": [{"type": "application", "name": "ci/sbom.py"}]},
            "component": {
                "type": "library",
                "bom-ref": root,
                "name": "rasterio",
                "version": version,
                "purl": root,
            },
        },
        "components": components,
        "dependencies": [
            {"ref": root, "dependsOn": [c["bom-ref"] for c in components]}
        ],
    }

    data = json.dumps(sbom, indent=2).encode()
    sbom_path = f"{dist_info}/sboms/rasterio.cdx.json"
    sha256 = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
    record_line = f"{sbom_path},sha256={sha256.decode()},{len(data)}\r\n"  # csv: \r\n
    tmp = wheel.with_suffix(".tmp")
    with zipfile.ZipFile(wheel) as zin, zipfile.ZipFile(tmp, "w") as zout:
        for info in zin.infolist():
            content = zin.read(info)
            if info.filename == record:
                sbom_info = zipfile.ZipInfo(sbom_path, info.date_time)
                sbom_info.external_attr = info.external_attr  # RECORD's file mode
                zout.writestr(sbom_info, data, zipfile.ZIP_DEFLATED)
                content += record_line.encode()
            zout.writestr(info, content)
    tmp.replace(wheel)
    print(f"{wheel.name}: {sbom_path} lists {len(components)} components")


if __name__ == "__main__":
    wheels = sorted(Path(sys.argv[1]).glob("*.whl"))
    if not wheels:
        sys.exit(f"no wheels in {sys.argv[1]}")
    pins = read_pins()
    for wheel in wheels:
        add_sbom(wheel, pins)

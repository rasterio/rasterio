"""Pytest marks for rasterio tests."""

import boto3
import pytest

from rasterio.env import GDALVersion

try:
    have_credentials = boto3.Session().get_credentials()
except Exception:
    have_credentials = False

credentials = pytest.mark.skipif(
    not (have_credentials), reason="S3 raster access requires credentials"
)

# Define helpers to skip tests based on GDAL version
gdal_version = GDALVersion.runtime()
requires_gdal3_11 = pytest.mark.skipif(
    not gdal_version.at_least("3.11"), reason="Requires GDAL 3.11.x"
)

requires_gdal_lt_3_11 = pytest.mark.skipif(
    gdal_version.at_least("3.11"), reason="Requires GDAL before 3.11"
)
requires_gdal3_12_1 = pytest.mark.skipif(
    not GDALVersion.runtime(include_patch=True).at_least("3.12.1", include_patch=True),
    reason="Requires GDAL 3.12.1 or later",
)
requires_gdal_lt_3_12_1 = pytest.mark.skipif(
    GDALVersion.runtime(include_patch=True).at_least("3.12.1", include_patch=True),
    reason="Requires GDAL before 3.12.1",
)

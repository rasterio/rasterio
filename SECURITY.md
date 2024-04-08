# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.3.x   | :white_check_mark: |
| < 1.3   | :x:                |

## Reporting a Vulnerability

Rasterio includes C extension modules that link [GDAL](https://gdal.org/), which in turn links a number of other libraries such as libtiff, libgeos, libproj, and libcurl.
The exact list depends on the features included when GDAL is built and varies across distributions.

The Rasterio project publishes binary wheels to the Python Package Index for 4 different platforms. The wheels contain 27-35 libraries.
The exact list depends on the platform and the versions of package managers and tooling used for each platform. Details can be found at https://github.com/rasterio/rasterio-wheels.

To report a vulnerability in rasterio or in one of the libraries that is included in a binary wheel on PyPI, please use the GitHub Security Advisory "Report a Vulnerability" tab. In the case of a vulnerability in a dependency, please provide a link to a published CVE or other description of the issue.

The Rasterio team will send a response indicating the next steps in handling your report. After the initial reply to your report, the security team will keep you informed of the progress towards a fix and full announcement at https://github.com/rasterio/rasterio/discussions, and may ask for additional information or guidance.

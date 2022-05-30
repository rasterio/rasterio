---
name: Report
about: Create a report to help us improve
---
<!--

WELCOME ABOARD!

Hi and welcome to the Rasterio project. We appreciate bug reports, questions
about documentation, and suggestions for new features. This issue template
isn't intended to ward you off; only to intercept and redirect some particular
categories of reports, and to collect a few important facts that issue reporters
often omit.

The primary forum for questions about installation and usage of Rasterio is 
https://rasterio.groups.io/g/main. The authors and other users will answer 
questions when they have expertise to share and time to explain. Please take the
time to craft a clear question and be patient about responses. Please do not
bring these questions to Rasterio's issue tracker, which we want to reserve for
bug reports and other actionable issues.

Questions about development of Rasterio, brainstorming, requests for comment,
and not-yet-actionable proposals are welcome in the project's developers 
discussion group https://rasterio.groups.io/g/dev. Issues opened in Rasterio's
GitHub repo which haven't been socialized there may be perfunctorily closed.

Please note: Rasterio contains extension modules and is thus susceptible to
C library compatibility issues. If you are reporting an installation or module
import issue, please note that this project only accepts reports about problems
with packages downloaded from the Python Package Index. Conda users should take
issues to one of the following trackers:

- https://github.com/ContinuumIO/anaconda-issues/issues
- https://github.com/conda-forge/rasterio-feedstock

You think you've found a bug? We believe you!
-->

## Expected behavior and actual behavior.

For example: I expected to read a band from a file and an exception occurred.

## Steps to reproduce the problem.

For example: a brief script with required inputs.

#### Environment Information
<!-- If you have rasterio>=1.3.0 -->
 - Output from: `rio --show-versions` or `python -c "import rasterio; rasterio.show_versions()"`
<!-- If you have rasterio<1.3.0 -->
 - rasterio version (`python -c "import rasterio; print(rasterio.__version__)"`)
 - GDAL version (`python -c "import rasterio; print(rasterio.__gdal_version__)"`)
 - Python version (`python -c "import sys; print(sys.version.replace('\n', ' '))"`)
 - Operation System Information (`python -c "import platform; print(platform.platform())"`)


## Installation Method

For example: the 1.0a11 manylinux1 wheel installed from PyPI using pip 9.0.1.

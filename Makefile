# Rasterio make file.

SHELL = /bin/bash

wheels: Dockerfile.wheels build-linux-wheels.sh
	docker build -f Dockerfile.wheels -t rasterio-wheelbuilder .
	docker run -v `pwd`:/io rasterio-wheelbuilder

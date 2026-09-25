PYTHON_VERSION ?= 3.12
GDAL ?= ubuntu-small-3.12.2
all: deps clean install test

.PHONY: docs

install:
	python setup.py build_ext
	pip install -e .[all]

deps:
	python -m pip install --upgrade pip
	pip install --group dev

clean:
	pip uninstall -y rasterio || echo "no need to uninstall"
	python setup.py clean --all
	find . -name '__pycache__' -delete -print -o -name '*.pyc' -delete -print
	touch rasterio/*.pyx

sdist:
	python setup.py sdist

test:
	py.test --maxfail 1 -v --cov rasterio --cov-report html --pdb tests

docs:
	pip install --group docs
	cd docs && make apidocs && make html

doctest:
	py.test --doctest-modules rasterio --doctest-glob='*.rst' docs/*.rst

dockertestimage:
	docker build --build-arg GDAL=$(GDAL) --build-arg PYTHON_VERSION=$(PYTHON_VERSION) --target gdal -t rasterio:$(GDAL)-py$(PYTHON_VERSION) .

dockertest: dockertestimage
	docker run --rm -it -v $(shell pwd):/app -v /tmp:/tmp --env AWS_ACCESS_KEY_ID --env AWS_SECRET_ACCESS_KEY --entrypoint=/bin/bash rasterio:$(GDAL)-py$(PYTHON_VERSION) -c '/venv/bin/python -m pip install -e . --group tests && /venv/bin/python -B -m pytest -m "not wheel" --cov rasterio --cov-report term-missing $(OPTS)'

dockershell: dockertestimage
	docker run -it -v $(shell pwd):/app --env AWS_ACCESS_KEY_ID --env AWS_SECRET_ACCESS_KEY --entrypoint=/bin/bash rasterio:$(GDAL)-py$(PYTHON_VERSION) -c '/venv/bin/python -m pip install . && /bin/bash'

dockersdist: dockertestimage
	docker run -it -v $(shell pwd):/app --env AWS_ACCESS_KEY_ID --env AWS_SECRET_ACCESS_KEY --entrypoint=/bin/bash rasterio:$(GDAL)-py$(PYTHON_VERSION) -c '/venv/bin/python -m build --sdist'

dockergdb: dockertestimage
	docker run -it -v $(shell pwd):/app --env AWS_ACCESS_KEY_ID --env AWS_SECRET_ACCESS_KEY --entrypoint=/bin/bash rasterio:$(GDAL)-py$(PYTHON_VERSION) -c '/venv/bin/python -m pip install -e . --group tests && gdb -ex=r --args /venv/bin/python -B -m pytest -m "not wheel" --cov rasterio --cov-report term-missing $(OPTS)'

dockerdocs: dockertestimage
	docker run -it -v $(shell pwd):/app --entrypoint=/bin/bash rasterio:$(GDAL)-py$(PYTHON_VERSION) -c 'source /venv/bin/activate && python -m pip install . --group docs && cd docs && make clean && make html'

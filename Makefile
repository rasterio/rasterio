all: deps clean install test

.PHONY: docs

install:
	python setup.py build_ext
	pip install -e .[all]

deps:
	pip install -r requirements-dev.txt

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
	cd docs && make apidocs && make html

doctest:
	py.test --doctest-modules rasterio --doctest-glob='*.rst' docs/*.rst

dockertestimage:
	docker build --build-arg GDAL=$(GDAL) --target gdal -t rasterio:$(GDAL) .

dockertest: dockertestimage
	docker run -it -v $(shell pwd):/app --env AWS_ACCESS_KEY_ID --env AWS_SECRET_ACCESS_KEY --entrypoint=/bin/bash rasterio:$(GDAL) -c '/venv/bin/python setup.py develop && /venv/bin/python -B -m pytest -rP -m "not wheel" --cov rasterio --cov-report term-missing $(OPTS)'

dockersdist: dockertestimage
	docker run -it -v $(shell pwd):/app --env AWS_ACCESS_KEY_ID --env AWS_SECRET_ACCESS_KEY --entrypoint=/bin/bash rasterio:$(GDAL) -c '/venv/bin/python setup.py sdist'

dockergdb: dockertestimage
	docker run -it -v $(shell pwd):/app --env AWS_ACCESS_KEY_ID --env AWS_SECRET_ACCESS_KEY --entrypoint=/bin/bash rasterio:$(GDAL) -c '/venv/bin/python setup.py develop && gdb -ex=r --args /venv/bin/python -B -m pytest -m "not wheel" --cov rasterio --cov-report term-missing $(OPTS)'

dockerdocs: dockertestimage
	docker run -it -v $(shell pwd):/app --entrypoint=/bin/bash rasterio:$(GDAL) -c 'source /venv/bin/activate && python -m pip install . && cd docs && make clean && make html'

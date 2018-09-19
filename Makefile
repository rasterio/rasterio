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

ARG GDAL=ubuntu-small-3.3.3
FROM osgeo/gdal:${GDAL} AS gdal 
ENV LANG="C.UTF-8" LC_ALL="C.UTF-8"
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3 python3-pip python3-dev python3-venv cython3 g++ gdb && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements*.txt ./
RUN python3 -m venv /venv && \
    /venv/bin/python -m pip install -U pip && \
    /venv/bin/python -m pip install -r requirements-dev.txt

FROM gdal
COPY . .
RUN /venv/bin/python setup.py install
ENTRYPOINT ["/venv/bin/rio"]
CMD ["--help"]

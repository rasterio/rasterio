ARG GDAL=ubuntu-small-3.3.3
ARG PYTHON_VERSION=3.8
FROM osgeo/gdal:${GDAL} AS gdal
ARG PYTHON_VERSION
ENV LANG="C.UTF-8" LC_ALL="C.UTF-8"
RUN apt-get update && apt-get install -y software-properties-common
RUN add-apt-repository -y ppa:deadsnakes/ppa
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    g++ \
    gdb \
    make \
    python3-pip \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-dev \
    python${PYTHON_VERSION}-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements*.txt ./
RUN python${PYTHON_VERSION} -m venv /venv && \
    /venv/bin/python -m pip install -U pip && \
    /venv/bin/python -m pip install -r requirements-dev.txt && \
    /venv/bin/python -m pip list

FROM gdal
COPY . .
RUN /venv/bin/python setup.py install
ENTRYPOINT ["/venv/bin/rio"]
CMD ["--help"]

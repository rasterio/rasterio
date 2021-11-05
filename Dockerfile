ARG GDAL=ubuntugis

FROM ubuntu:20.04 AS ubuntugis
ENV LANG="C.UTF-8" LC_ALL="C.UTF-8"
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3 python3-pip python3-dev python3-venv cython3 g++ libgdal-dev gdal-bin && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /tmp
COPY . .
RUN python3 -m venv /venv && /venv/bin/python -m pip install -U pip && /venv/bin/python -m pip install -r requirements-dev.txt

FROM ubuntugis AS latest
RUN echo "hi!"

FROM ${GDAL} AS rio
RUN /venv/bin/python -m pip install .
WORKDIR /usr/src/app
COPY tests ./tests
ENTRYPOINT ["/venv/bin/rio"]
CMD ["--help"]

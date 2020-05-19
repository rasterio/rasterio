FROM ubuntu:20.04

WORKDIR /usr/src/app

ENV LANG="C.UTF-8" LC_ALL="C.UTF-8"

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3 python3-pip python3-dev cython3 g++ libgdal-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

COPY . .
RUN python3 setup.py install

ENTRYPOINT ["rio"]
CMD ["--help"]

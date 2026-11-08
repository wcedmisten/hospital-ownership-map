FROM postgis/postgis:16-3.4

RUN apt-get update && apt-get install -y unzip gdal-bin \
  # osm2pgsql build dependencies
  make cmake g++ libboost-dev \
  libexpat1-dev zlib1g-dev libpotrace-dev \
  libopencv-dev libbz2-dev libpq-dev libproj-dev lua5.3 liblua5.3-dev \
  pandoc nlohmann-json3-dev pyosmium

ADD https://github.com/osm2pgsql-dev/osm2pgsql/archive/refs/tags/2.0.0.zip osm2pgsql-dev.zip
RUN unzip osm2pgsql-dev.zip

RUN mkdir /osm2pgsql-2.0.0/build && cd /osm2pgsql-2.0.0/build
RUN cmake /osm2pgsql-2.0.0
RUN make
RUN make install

RUN apt-get install -y pip python3
RUN pip install pandas psycopg psycopg2-binary pyarrow

COPY postgresql.conf /postgresql.conf
COPY hospitals.lua /hospitals.lua

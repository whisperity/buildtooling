FROM PREVIOUS_IMAGE

RUN apt-get install --yes \
  binutils \
  wget

# To build Xerces, we need some additional libraries:
RUN apt-get install --yes \
  curl \
  libcurl4-openssl-dev

RUN wget "http://www.apache.org/dyn/mirrors/mirrors.cgi?action=download&filename=xerces/c/3/sources/xerces-c-3.2.1.tar.gz" \
    -O "xerces-c-3.2.1.tar.gz" && \
  tar vxf xerces-c-3.2.1.tar.gz && \
  mv xerces-c-3.2.1 /usr/src/xerces-c && \
  rm xerces-c-3.2.1.tar.gz

RUN ln -s /usr/src/xerces-c /tmp/source

FROM ubuntu:18.04

ENV DEBIAN_FRONTEND="noninteractive"

RUN apt-get update

# Install useful system utilities.
RUN apt-get install --yes \
  git \
  time \
  tree \
  vim \
  wget

# Install the compiler stuff required.
RUN apt-get install --yes \
  binutils \
  cmake \
  clang \
  g++ \
  libtinfo-dev \
  make \
  python

# Grab the source code of ZapCC and compile it.
# At the writing of this, master was at
# `35fa2aed76fffa222db340dcb9257f66dc858d42`.
RUN git clone http://github.com/yrnkrn/zapcc.git \
      --depth 1 \
      --single-branch \
      --origin upstream \
      /usr/src/zapcc && \
  rm -rf /usr/src/zapcc/.git

# There seems to be something amiss with building this image, the dependencies
# could be badly ordered because by default Docker runs with 'POSIX' locale.
# This two commands try to fix this, changing the running image to 'enUS'.
RUN apt-get install --yes locales && \
  sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
  dpkg-reconfigure --frontend=noninteractive locales && \
  update-locale LANG=en_US.UTF-8
ENV LANG en_US.UTF-8

# The build is executed via a shell command that runs must be run as a shell
# script as opposed to a `RUN` action here, because processor count and such
# should be used for the build, but it does not affect the result of the image
# that is being built.
COPY build-zapcc.sh /tmp/build.sh
RUN mkdir /tmp/build && \
  cd /tmp/build && \
  cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DLLVM_USE_LINKER=gold \
    /usr/src/zapcc/ && \
  /tmp/build.sh && \
  cd /tmp && \
  rm -rf ./build build.sh

WORKDIR /tmp

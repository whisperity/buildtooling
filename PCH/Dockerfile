FROM ubuntu:18.04
ENV DEBIAN_FRONTEND="noninteractive"
RUN apt-get update
RUN apt-get install --yes \
  bsdmainutils \
  less \
  time \
  tree \
  vim

RUN apt-get install --yes \
  clang \
  cmake \
  g++ \
  make

WORKDIR /tmp

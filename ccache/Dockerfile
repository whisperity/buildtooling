FROM ubuntu:18.04

ENV DEBIAN_FRONTEND="noninteractive"

RUN apt-get update

# Install useful system utilities.
RUN apt-get install --yes \
  time \
  tree \
  vim

# Install the compiler stuff required.
RUN apt-get install --yes \
cmake \
  clang \
  g++ \
  ccache \
  make

# Set up CCache as wrapper.
ENV PATH="/usr/lib/ccache:${PATH}"
RUN /usr/sbin/update-ccache-symlinks
WORKDIR /tmp


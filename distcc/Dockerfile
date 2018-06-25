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
  clang \
  cmake \
  distcc \
  distcc-pump \
  g++ \
  make

WORKDIR /tmp
COPY usage.md /tmp/USAGE.md

# Copy a script that automatically starts the DistCC daemon when the image is
# created.
COPY start-distcc.sh /bin/start-distcc
ENTRYPOINT /bin/start-distcc

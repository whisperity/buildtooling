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
  clang \
  cmake \
  g++ \
  make

# Install dependencies for Bazel.
RUN apt-get install --yes \
  pkg-config \
  python \
  unzip \
  zip \
  zlib1g-dev

RUN wget http://github.com/bazelbuild/bazel/releases/download/0.15.0/bazel-0.15.0-installer-linux-x86_64.sh -O bazel.sh && \
  chmod +x bazel.sh && \
  bash ./bazel.sh --prefix=/usr && \
  rm bazel.sh && \
  echo 'source /usr/lib/bazel/bin/bazel-complete.bash' >> ~/.bashrc

ENV PATH="${HOME}/bin:${PATH}"

WORKDIR /tmp
COPY USAGE.md USAGE.md
RUN git clone https://github.com/bazelbuild/examples/

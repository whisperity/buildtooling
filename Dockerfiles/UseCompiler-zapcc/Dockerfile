FROM PREVIOUS_IMAGE AS zapcc_build

RUN apt-get install --yes \
  binutils \
  cmake \
  clang \
  git \
  libtinfo-dev \
  make \
  python

# There seems to be something amiss with building this image, the dependencies
# could be badly ordered because by default Docker runs with 'POSIX' locale.
# This two commands try to fix this, changing the running image to 'enUS'.
RUN apt-get install --yes locales && \
  sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
  dpkg-reconfigure --frontend=noninteractive locales && \
  update-locale LANG=en_US.UTF-8
ENV LANG en_US.UTF-8

RUN git clone http://github.com/yrnkrn/zapcc.git \
    --depth 1 \
    --single-branch \
    --origin upstream \
    /usr/src/zapcc && \
  cd /usr/src/zapcc && \
  echo "Current ZapCC HEAD hash is: $(git rev-parse HEAD)"

RUN mkdir /tmp/build /tmp/install && \
  cd /tmp/build && \
  cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/tmp/install \
    -DLLVM_TARGETS_TO_BUILD=X86 \
    -DLLVM_USE_LINKER=gold \
    /usr/src/zapcc/

RUN nproc > /tmp/nproc

# Two or three 'make' calls should be executed because for some reason the
# 'Attribute.gen' generation fails on the initial 'make' call.
WORKDIR /tmp/build
RUN NPROC=$(cat /tmp/nproc); \
  make -k -j${NPROC}; \
  make -k -j${NPROC}; \
  make -k -j${NPROC}; \
  make install

# Use a new image and only copy the built ZapCC for usage - no need for rest.
FROM PREVIOUS_IMAGE

COPY --from=zapcc_build /tmp/install/ /

# To allow ZapCC to act as a compiler, install the standard libraries by hand.
RUN apt-get install --yes \
  libc6-dev \
  libstdc++-7-dev

ENV CC="zapcc"
ENV CXX="zapcc++"

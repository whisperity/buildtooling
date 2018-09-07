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

WORKDIR /tmp/build
RUN NPROC=$(cat /tmp/nproc); \
  touch /tmp/install/foo && \
  mkdir /tmp/install/bin && \
  touch /tmp/install/bin/dummy && \
  chmod +x /tmp/install/bin/dummy
# TODO: Test if actually works if I have the hardware...
#  make -k -j${NPROC} && \
#  make install

# Use a new image and only copy the built ZapCC for usage - no need for rest.
FROM PREVIOUS_IMAGE

COPY --from=zapcc_build /tmp/install/ /

ENV CC="zapcc"
ENV CXX="zapcc++"

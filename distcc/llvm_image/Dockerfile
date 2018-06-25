# 64M shared memory size (the default) is NOT enough to run DistCC with "pump"
# mode. Use `--shm-size 1G` or something like that at starting the CONTAINER
# built from this image!

FROM distcc-test-image

ENV DEBIAN_FRONTEND="noninteractive"

RUN apt-get install --yes \
  binutils \
  git \
  wget

RUN wget http://releases.llvm.org/6.0.0/llvm-6.0.0.src.tar.xz && \
  wget http://releases.llvm.org/6.0.0/cfe-6.0.0.src.tar.xz && \
  wget http://releases.llvm.org/6.0.0/clang-tools-extra-6.0.0.src.tar.xz && \
  tar xvf llvm-6.0.0.src.tar.xz && \
  tar xvf cfe-6.0.0.src.tar.xz && \
  tar xvf clang-tools-extra-6.0.0.src.tar.xz && \
  mv llvm-6.0.0.src llvm && \
  mv cfe-6.0.0.src llvm/tools/clang && \
  mv clang-tools-extra-6.0.0.src llvm/tools/clang/tools/extra && \
  mv llvm /usr/src/llvm && \
  rm *.tar.xz

RUN ln -s /usr/src/llvm source && \
  mkdir build build-distcc

RUN cd build && \
  cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=ON \
    -DLLVM_USE_LINKER=gold \
    ../source/

RUN cd build-distcc && \
  cmake \
    -DCMAKE_C_COMPILER_LAUNCHER="distcc" \
    -DCMAKE_CXX_COMPILER_LAUNCHER="distcc" \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=ON \
    -DLLVM_USE_LINKER=gold \
    ../source/


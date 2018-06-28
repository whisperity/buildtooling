FROM zapcc-test-image

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
  mkdir build-gcc build-clang build-zapcc

RUN cd build-gcc && \
  cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=ON \
    -DLLVM_USE_LINKER=gold \
    ../source/

RUN cd build-clang && \
  cmake \
    -DCMAKE_C_COMPILER="clang" \
    -DCMAKE_CXX_COMPILER="clang++" \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=ON \
    -DLLVM_USE_LINKER=gold \
    ../source/

RUN cd build-zapcc && \
  cmake \
    -DCMAKE_C_COMPILER="zapcc" \
    -DCMAKE_CXX_COMPILER="zapcc++" \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=ON \
    -DLLVM_USE_LINKER=gold \
    ../source/


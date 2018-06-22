FROM ccache-test-image

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
  mkdir build_static \
    build_dynamic

RUN cd build_static && \
  cmake ../source/

RUN cd build_dynamic && \
  cmake -DCMAKE_BUILD_TYPE=Release \
    -DLLVM_TARGETS_TO_BUILD=X86 \
    -DBUILD_SHARED_LIBS=ON \
    -DLLVM_USE_LINKER=gold \
    ../source/

RUN ccache --clear --max-files=0 --max-size=0 --zero-stats

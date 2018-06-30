FROM pch-test-image

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

# TODO: Create a Translation Unit that contains every header of LLVM and
# a command that compiles it. :)
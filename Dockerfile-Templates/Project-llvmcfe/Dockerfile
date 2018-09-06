FROM PREVIOUS_IMAGE

RUN apt-get install --yes \
  binutils \
  cmake \
  python \
  wget

RUN wget "http://releases.llvm.org/6.0.0/llvm-6.0.0.src.tar.xz" && \
  wget "http://releases.llvm.org/6.0.0/cfe-6.0.0.src.tar.xz" && \
  wget "http://releases.llvm.org/6.0.0/clang-tools-extra-6.0.0.src.tar.xz" && \
  tar vxf llvm-6.0.0.src.tar.xz && \
  tar vxf cfe-6.0.0.src.tar.xz && \
  tar vxf clang-tools-extra-6.0.0.src.tar.xz && \
  mv llvm-6.0.0.src llvm && \
  mv cfe-6.0.0.src llvm/tools/clang && \
  mv clang-tools-extra-6.0.0.src llvm/tools/clang/tools/extra && \
  mv llvm /usr/src/llvm && \
  rm *.tar.xz

RUN ln -s /usr/src/llvm /tmp/source

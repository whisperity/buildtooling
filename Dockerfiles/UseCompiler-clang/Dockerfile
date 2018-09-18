FROM PREVIOUS_IMAGE AS clang_build

RUN apt-get install --yes \
  binutils \
  cmake \
  clang \
  git \
  libtinfo-dev \
  make \
  python \
  unzip \
  wget

# TODO: Workaround code that downloads and builds Clang 7.

RUN wget "https://github.com/llvm-mirror/llvm/archive/release_70.zip" -O llvm.zip&& \
  wget "https://github.com/llvm-mirror/clang/archive/release_70.zip" -O clang.zip && \
  wget "https://github.com/llvm-mirror/clang-tools-extra/archive/release_70.zip" -O cte.zip && \
  unzip llvm.zip && \
  unzip clang.zip && \
  unzip cte.zip && \
  mv llvm-release_70 llvm && \
  mv clang-release_70 llvm/tools/clang && \
  mv clang-tools-extra-release_70 llvm/tools/clang/tools/extra && \
  mv llvm /usr/src/llvm && \
  rm *.zip

RUN mkdir /tmp/build /tmp/install && \
  cd /tmp/build && \
  cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/tmp/install \
    -DLLVM_TARGETS_TO_BUILD=X86 \
    -DLLVM_USE_LINKER=gold \
    /usr/src/llvm

WORKDIR /tmp/build

RUN NPROC=$(nproc); \
  make -k -j${NPROC}; \
  make -j${NPROC} install


FROM PREVIOUS_IMAGE

COPY --from=clang_build /tmp/install /

# TODO: Change to Clang-7 once it hits upstream package sources.
# RUN apt-get install --yes \
#   clang

# Only used because copied-over Clang needs some standard libraries to use.
# TODO: REMOVE.
RUN apt-get install --yes libc6-dev libstdc++-7-dev

ENV CC="clang"
ENV CXX="clang++"

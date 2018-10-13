FROM PREVIOUS_IMAGE AS cmake_build

RUN apt-get install --yes \
  g++ \
  make

ENV CC="gcc"
ENV CXX="g++"

RUN nproc > /tmp/nproc

# Build our custom version of CMake for now, because this feature is under
# review to be integrated into upstream CMake.
RUN git clone "http://gitlab.kitware.com/Whisperity/CMake.git" \
    /usr/src/cmake && \
  cd /usr/src/cmake && \
  echo "Current CMake master hash is: $(git rev-parse origin/master)" && \
  echo "Current CMake topic hash is: $(git rev-parse origin/clang-modules)"

RUN cd /usr/src/cmake && \
  ./bootstrap --parallel=$(cat /tmp/nproc) --prefix="/tmp/install" && \
  git checkout clang-modules && \
  make install -j$(cat /tmp/nproc)

FROM PREVIOUS_IMAGE
#ifndef COMPILER_clang
#error A Modules-enabled project cannot be used without the LLVM/Clang compiler.
#endif

# Install our custom version of CMake.
RUN apt-get purge --yes \
  cmake && \
  apt-get autoremove --yes

COPY --from=cmake_build /tmp/install /

# Build Xerces.
RUN apt-get install --yes \
  binutils \
  wget \
  unzip

# To build Xerces, we need some additional libraries:
RUN apt-get install --yes \
  curl \
  libcurl4-openssl-dev

# This "randomise" preprocessor pseudo-directive instructs the Python wrangler
# to always randomise the value defined as the given macro. This results in
# Docker not being able to cache the build results here, essentially allowing
# us to fetch the features over and over again.
#randomise SOME_RANDOM_VALUE
ENV RAND=SOME_RANDOM_VALUE

RUN wget "http://github.com/whisperity/xerces-c-modules/archive/modules.zip" -O "modules.zip" && \
  unzip modules.zip && \
  mv xerces-c-modules-modules /usr/src/xerces-c && \
  rm modules.zip

RUN ln -s /usr/src/xerces-c /tmp/source

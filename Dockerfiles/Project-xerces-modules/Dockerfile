#ifndef COMPILER_clang
#error A Modules-enabled project cannot be used without the LLVM/Clang compiler.
#endif

FROM PREVIOUS_IMAGE

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

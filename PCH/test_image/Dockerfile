FROM pch-test-image

RUN mkdir -p /usr/src && \
  ln -s /usr/src sources

# Create a sample PCH of a few things for inspection.
COPY sample.h /usr/src/sample.h
RUN clang++ -xc++-header /usr/src/sample.h -o /tmp/sample.h.pch
RUN g++ -xc++-header /usr/src/sample.h -o /tmp/sample.h.gch

# Compile some dummy project with PCHs via a compile script written directly.
COPY direct /tmp/direct
RUN cd /tmp/direct && \
  ./compile.sh

# Do the same with G++
COPY direct /tmp/direct-gcc
RUN cd /tmp/direct-gcc && \
  ./compile-gcc.sh

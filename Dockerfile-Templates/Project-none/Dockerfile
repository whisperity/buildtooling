FROM PREVIOUS_IMAGE

RUN apt-get install --yes \
  make

#depends "hello.c"
#depends "Makefile"
COPY hello.c /usr/src/hello.c
COPY Makefile /usr/src/Makefile

WORKDIR /tmp
RUN ln -s /usr/src/Makefile /tmp/Makefile && \
  ln -s /usr/src/hello.c /tmp/hello.c

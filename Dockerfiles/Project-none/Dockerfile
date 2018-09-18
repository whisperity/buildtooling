FROM PREVIOUS_IMAGE

#depends "hello.c"
#depends "make"
COPY hello.c /usr/src/hello.c
COPY make /usr/src/make

WORKDIR /tmp
RUN ln -s /usr/src/make /tmp/make && \
  ln -s /usr/src/hello.c /tmp/hello.c

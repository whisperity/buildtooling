FROM ccache-test-image

COPY source /usr/src/source
RUN ln -s /usr/src/source source && \
  cmake source/

RUN ccache --clear --max-files=0 --max-size=0 --zero-stats

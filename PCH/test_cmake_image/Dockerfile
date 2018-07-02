FROM pch-test-image

RUN apt-get install --yes \
  wget

RUN wget https://github.com/sakra/cotire/releases/download/cotire-1.8.0/cotire.cmake && \
  mv cotire.cmake /usr/share/cmake-*/Modules/

COPY source /usr/src/source
RUN ln -s /usr/src/source source && \
  cmake source/


FROM PREVIOUS_IMAGE

RUN apt-get install --yes \
  cmake

WORKDIR /tmp

RUN cp -R /usr/src/xerces-c build && \
  cd build && \
  cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="/" \
#ifdef TOOL_distcc
    -DCMAKE_C_COMPILER_LAUNCHER="distcc" \
    -DCMAKE_CXX_COMPILER_LAUNCHER="distcc" \
#endif
    ../source/

#ifdef TOOL_ccache
# Clear CCache statistics registered due to configuration of project.
RUN ccache --clear --max-files=0 --max-size=0 --zero-stats
#endif

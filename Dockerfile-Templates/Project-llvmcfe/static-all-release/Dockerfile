FROM PREVIOUS_IMAGE

WORKDIR /tmp

RUN mkdir build && \
  cd build && \
  cmake \
    -DCMAKE_BUILD_TYPE=Release \
#ifdef TOOL_distcc
    -DCMAKE_C_COMPILER_LAUNCHER="distcc" \
    -DCMAKE_CXX_COMPILER_LAUNCHER="distcc" \
#endif
    ../source/

#ifdef TOOL_ccache
# Clear CCache statistics registered due to configuration of project.
RUN ccache --clear --max-files=0 --max-size=0 --zero-stats
#endif

FROM PREVIOUS_IMAGE

RUN apt-get install --yes \
  ccache

# Set up CCache as a wrapper.
ENV PATH="/usr/lib/ccache:${PATH}"
RUN /usr/sbin/update-ccache-symlinks

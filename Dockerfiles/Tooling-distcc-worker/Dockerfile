# TODO: If multiple tools are allowed, don't allow this image to be built with
# 'distcc' tool also enabled.

FROM PREVIOUS_IMAGE

# Pull 'tini' (tiny but valid init script) to the current image so that the
# daemon can be run in the background properly.
COPY --from=krallin/ubuntu-tini:latest /usr/bin/tini /sbin/tini

RUN apt-get install --yes \
  distcc

#depends "start-distcc.sh"
COPY start-distcc.sh /bin/start-distcc.sh
RUN chmod +x /bin/start-distcc.sh

# DistCC listens on a TCP socket.
EXPOSE 3632/tcp

# The tiny init should be used to reap the processes in case of a container
# shutdown.
ENTRYPOINT ["/sbin/tini", "--", "/bin/start-distcc.sh"]

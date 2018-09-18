FROM PREVIOUS_IMAGE

RUN apt-get install --yes \
  distcc \
  distcc-pump

#depends "distcc-welcome.sh"
COPY distcc-welcome.sh /tmp/distcc-welcome.sh
RUN cat /tmp/distcc-welcome.sh >> /etc/bash.bashrc && \
  rm /tmp/distcc-welcome.sh

#depends "distcc-hosts"
COPY distcc-hosts /bin/distcc-hosts
RUN chmod +x /bin/distcc-hosts

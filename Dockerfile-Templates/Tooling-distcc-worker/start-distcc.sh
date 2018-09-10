#!/bin/bash

if [ -z "${NPROC}" ]
then
  NPROC=$(nproc)
fi

if [ $# -ne 0 ]
then
  echo "Overridden start arguemnts found - executing the command itself." >&2
  exec "$@"
else
  # Create a DistCC daemon.
  distccd \
    --allow 0.0.0.0/0 \
    --daemon \
    --no-detach \
    --pid-file=/var/run/distccd.pid \
    --log-file=/var/log/distccd.log \
    --jobs ${NPROC}
fi


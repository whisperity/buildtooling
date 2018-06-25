#!/bin/bash

# Make sure the DistCC compilations use the server running on the local machine
# started by this strict. No local compilations under the invoking
# client's tree will be used. (`localhost` here would mean absolutely local,
# that's why IPv4 loopback is used.)
export DISTCC_HOSTS="127.0.0.1/$(nproc),cpp,lzo"

# Create a DistCC daemon.
distccd \
  --allow 0.0.0.0/0 \
  --daemon \
  --log-stderr \
  --jobs $(nproc) \
  &

# Start the Pump mode server.
eval $(distcc-pump --startup)

# Start a Bash shell that communicates with the user.
bash

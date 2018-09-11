#!/bin/bash

# ----------------------------------------------------------------------------
#  This is script is used in a distcc tooled compilation environment to warn
#  the user that 'DISTCC_HOSTS' environment variable must be set accordingly,
#  and also helps the user executing the image to quickly add hosts with the
#  appropriate format.
# ----------------------------------------------------------------------------

if [ -z "${DISTCC_HOSTS}" ]
then
  echo "Please make sure that 'DISTCC_HOSTS' is set appropriately before "
  echo "executing the compiler calls."
  echo
  echo "Please use the command 'distcc_host_add <hostname> <jobs> [port] "
  echo "to add the DistCC server running at hostname:port with max jobs "
  echo "jobs to the list of servers used."
fi

# ----------------------------------------------------------------------------

__load_additional_distcc_host() {
  # Load a distcc host value from the temporary file if it exists.
  if [ -f /tmp/add-distcc ]
  then
    eval $(cat /tmp/add-distcc)
    rm /tmp/add-distcc
  fi
}

PROMPT_COMMAND="__load_additional_distcc_host;${PROMPT_COMMAND}"

distcc_host_add() {
  HOST="$1"
  JOBS="$2"
  PORT="$3"

  if [ -z "${HOST}" ]
  then
    echo "Usage: distcc_host_add <hostname> <jobs> [port]" >&2
    return
  fi

  if [ -z "${JOBS}" ]
  then
    JOBS="$(nproc)"
  fi

  if [ -z "${PORT}" ]
  then
    PORT="3632" # Default port for distcc.
  fi

  re='^[0-9]+$'
  if ! [[ ${PORT} =~ $re ]]
  then
    echo "error: 'port' must be a number." >&2
    exit 1
  fi
  if ! [[ ${JOBS} =~ $re ]]
  then
    echo "error: 'jobs' must be a number." >&2
    exit 1
  fi

  echo "export DISTCC_HOSTS=\"${HOST}:${PORT}/${JOBS},cpp,lzo "'${DISTCC_HOSTS}'" \"" >> /tmp/add-distcc
}


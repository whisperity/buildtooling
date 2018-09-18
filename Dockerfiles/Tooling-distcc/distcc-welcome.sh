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

echo
echo "Type 'distcc-hosts' to check which remote servers are configured."
echo

if [ -f /etc/distcc-min-shm-size ]
then
  MIN_SIZE=$(cat /etc/distcc-min-shm-size)
  CUR_SIZE=$(df /dev/shm | tail -n +2 | awk '{print $2}')
  if [ $CUR_SIZE -lt $MIN_SIZE ]
  then
    echo "The project used specifies a distcc minimum shared memory size "
    echo "of '${MIN_SIZE}' bytes for 'distcc-pump' mode to work."
    echo "Current configured shared memory is '${CUR_SIZE}' bytes."
    echo
    echo "Pump mode will be disabled! Please create a new container with the "
    echo "extra option '--shm-size ${CUR_SIZE}' specified."

    PUMP_BINARY=$(which distcc-pump)
    # Just purge the 'pump' binary completely...
    apt-get purge -qqy distcc-pump 2>&1 >/dev/null

    cat << EOF > ${PUMP_BINARY}
#!/bin/bash
echo "DistCC Pump mode is disabled because shared memory is too small for this project."
echo "Please start a new container with '--shm-size ${CUR_SIZE}' specified."
exit 1
EOF
    chmod +x ${PUMP_BINARY}
  fi
fi


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


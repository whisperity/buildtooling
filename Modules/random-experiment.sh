#!/bin/bash

CCDB="$1"
OUTMOD="$2"
NUM_PER_BUCKET_SIZE="$3"
shift 3

mkdir -pv "./random-experiment-results/"

# Get the analysis done.
rm -f ./RandomModule_*.cppm
__main__.py "$CCDB" "$OUTMOD" --force-reanalysis --dry-run --jobs $(nproc) 2>&1 | tee "./random-experiment-results/BASELINE.LOG"

# NUM_CPPMS=$(find . -name "*.cppm" -type f | wc -l)
# for i in $(seq 2 "$(( ${NUM_CPPMS} - 1))")

for i in "$@"
do
  for n in $(seq 1 ${NUM_PER_BUCKET_SIZE})
  do
    rm -f ./RandomModule_*.cppm
    git reset --hard
    random-cppms.py . "${i}" 2>&1 | tee "./random-experiment-results/${i}_${n}-$(date | tr ' ' '-').log"
    __main__.py "$CCDB" "$OUTMOD" --jobs "$(nproc)" --profile --dry-run 2>&1 | tee --append "./random-experiment-results/${i}_${n}-$(date | tr ' ' '-').log"
  done
done

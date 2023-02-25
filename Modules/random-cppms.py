#!/usr/bin/env python3

import argparse
import datetime
import math
import os
import random
import sys
import time

from ModulesTSMaker import mapping
from utils.progress_bar import tqdm

# ------------------- Set up the command-line configuration -------------------

PARSER = argparse.ArgumentParser(
    prog='random-cppm',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description="Randomly distributes the CPPM Modules files in the current "
                "tree to the specified number of modules instead.")

PARSER.add_argument("project_dir",
                    type=str,
                    help="Path to the master root directory of the project "
                         "under analysis.")

PARSER.add_argument("num_buckets",
                    type=int,
                    help="The number of modules to group the found original "
                         "modules into.")

ARGS = PARSER.parse_args()

if ARGS.num_buckets <= 0:
    print("ERROR: Negative number of buckets.", file=sys.stderr)
    sys.exit(2)

# ------------------------- Real execution begins now -------------------------

RANDOM = random.SystemRandom()

START_AT = time.time()

# First, load all the modules in the current tree and build a data structure as
# to where and what they are.

ModuleMap, _ = mapping.get_module_mapping(ARGS.project_dir)

buckets = [list() for _ in range(ARGS.num_buckets)]

print("Distributing %d modules to %d buckets..." %
      (len(ModuleMap), len(buckets)))
avg_size = round(len(ModuleMap) / len(buckets))
print("Expected average count [%d / %d] = %d" %
      (len(ModuleMap), len(buckets), avg_size))
expected_sd = round(math.sqrt((avg_size ** 2) / 12.0))
print("Expected standard deviation [√( (%d - 0)^2 / 12)] = %d" %
      (avg_size, expected_sd))
max_overflow = round(expected_sd / 2.0)
print("Max. allowed excess above average per bucket [SD / 2] = %d" %
      max_overflow)

for module in tqdm(ModuleMap,
                   desc="Distributing modules...",
                   unit="module"):
    to_bucket_idx = RANDOM.randint(0, len(buckets) - 1)
    buckets[to_bucket_idx].append(module)

print("Module counts in buckets 1-%d:" % len(buckets),
      [len(b) for b in buckets])
print("Deviance from average (%d):" % avg_size,
      [len(b) - avg_size for b in buckets])

excess_buckets = set()
excess = list()
max_element_count = avg_size + max_overflow
for i, bucket in enumerate(tqdm(buckets,
                                desc="Trimming excess...",
                                unit="bucket")):
    if len(bucket) > max_element_count:
        excess_buckets.add(i)
        # If the bucket is overfull more than a standard deviation from the
        # average, trim some excess modules from it randomly... (1)
        selected_excess = RANDOM.sample(bucket,
                                        len(bucket) - max_element_count)
        for m in selected_excess:
            print("Removed module '%s' from bucket #%d" %
                  (ModuleMap.get_filename(m), i + 1))
            excess.append(m)
            bucket.remove(m)
        buckets[i] = bucket

if excess:
    print("Bucket # that contained excess and was trimmed:",
          list(excess_buckets))
    print("# of excess modules for redistribution:", len(excess))

    allowed_buckets = set(range(0, len(buckets))) - excess_buckets
    allowed_buckets = list(allowed_buckets)
    print("Bucket # that may receive excess:", allowed_buckets)

    for m in tqdm(excess, desc="Distributing excess...", unit="module"):
        # Assign the module to a bucket that is still available, randomly.
        to_bucket_idx = RANDOM.choice(allowed_buckets)
        buckets[to_bucket_idx].append(m)
        print("Assigned module '%s' to bucket #%d" % (m, to_bucket_idx + 1))
        if len(buckets[to_bucket_idx]) >= max_element_count:
            print("Bucket #%d is now full, may no longer receive excess..."
                  % (to_bucket_idx + 1))
            allowed_buckets.remove(to_bucket_idx)

    print("Module counts in buckets 1-%d:" % len(buckets),
          [len(b) for b in buckets])
    print("Deviance from average (%d):" % avg_size,
          [len(b) - avg_size for b in buckets])

for i, bucket in enumerate(tqdm(buckets,
                           desc="Emitting merged modules",
                           unit="module",
                           position=1,
                           leave=True)):
    module_output_file = os.path.join(ARGS.project_dir,
                                      "RandomModule_%d.cppm" % i)
    with open(module_output_file, 'w') as out:
        # Print the module heading in the expected output format.
        print("#define MODULE_EXPORT", file=out)
        print(file=out)
        print("export module FULL_NAME__RandomModule_%d;" % i, file=out)
        print(file=out)

        for module in tqdm(bucket,
                           desc="Rewriting contents",
                           unit="module-file",
                           position=0,
                           leave=False):
            for fragment in ModuleMap.get_fragment_list(module):
                print("#include \"%s\"" % fragment, file=out)

            os.remove(ModuleMap.get_filename(module))

END_AT = time.time()

# --------------------------------- Profiling ---------------------------------

print("====================================================================")
print("Execution started at %s.\n"
      % datetime.datetime.fromtimestamp(START_AT)
      .strftime(r'%Y-%m-%d %H:%M:%S.%f'))
print("Execution ended at %s."
      % datetime.datetime.fromtimestamp(END_AT)
      .strftime(r'%Y-%m-%d %H:%M:%S.%f'))
print("Total execution took %s wall time."
      % datetime.timedelta(seconds=END_AT - START_AT))

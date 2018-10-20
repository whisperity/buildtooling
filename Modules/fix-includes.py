#!/usr/bin/env python3

import os
import sys

try:
  import toposort
except ImportError as e:
  print("Error! A dependency of this tool could not be satisfied. Please "
        "install the following Python package via 'pip' either to the "
        "system, or preferably create a virtualenv.")
  print(str(e))
  sys.exit(1)

import utils
from utils import walk_folder
from utils.progress_bar import tqdm
from ModulesTSMaker import *


if not os.path.isfile("CMakeLists.txt"):
  print("Error: this script should be run from a source folder.",
        file=sys.stderr)
  sys.exit(2)


MODULEMAP = mapping.get_module_mapping(os.getcwd())
MODULEMAP, duplicates = utils.eliminate_dict_listvalue_duplicates(MODULEMAP)

if duplicates:
  print("Error: Some files are included into multiple modules. These files "
        "had been removed from the mapping!", file=sys.stderr)
  print('\n'.join(duplicates), file=sys.stderr)


SELF_DEPENDENCY_MAP = {}

# Check for headers that may or may not have an implementation CPP to them.
for file in tqdm(walk_folder(os.getcwd()),
                 unit='files',
                 desc="Iface-Impl pairs",
                 total=len(list(walk_folder(os.getcwd()))),
                 position=1):
  if not file.endswith('.hpp'):
    continue

  cpp_path = file.replace('.hpp', '.cpp')
  if not os.path.isfile(cpp_path):
    # If the header does not have an implementation pair, do only the header.
    cpp_path = None

  include.handle_source_text(MODULEMAP, SELF_DEPENDENCY_MAP,
                             file, util.concatenate_files(file, cpp_path))

# Check for source files that do not have a header named like them.
for file in tqdm(walk_folder(os.getcwd()),
                 unit='files',
                 desc="Solo impl. files",
                 total=len(list(walk_folder(os.getcwd()))),
                 position=1):
  if not file.endswith('.cpp'):
    continue

  hpp_path = file.replace('.cpp', '.hpp')
  if os.path.isfile(hpp_path):
    # If the implementation file had a header pair with it, it is already
    # handled.
    continue

  include.handle_source_text(MODULEMAP, SELF_DEPENDENCY_MAP,
                             file, util.concatenate_files(None, file))

import json
#print(json.dumps(SELF_DEPENDENCY_MAP, indent=2, sort_keys=True))

for module in SELF_DEPENDENCY_MAP.keys():
  try:
    topo = toposort.toposort(SELF_DEPENDENCY_MAP[module])
    topo = list(topo)
    print("MODULE %s DEPENDENCIES" % module)
    topo = [list(x) for x in list(topo)]  # Convert sets to lists...
    print(json.dumps(topo, indent=2, sort_keys=False))
  except toposort.CircularDependencyError:
    # print("Circular dependency in module '%s'." % module, file=sys.stderr)
    # print("Ignoring for now...", file=sys.stderr)
    pass

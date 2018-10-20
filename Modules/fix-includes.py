#!/usr/bin/env python3

import codecs
import os
import re
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


HEADER_FILE = re.compile(r'\.(H(XX|PP|\+\+)?|h(xx|pp|\+\+)?|t(xx|pp|\+\+))$')

if not os.path.isfile("CMakeLists.txt"):
  print("Error: this script should be run from a source folder.",
        file=sys.stderr)
  sys.exit(2)


MODULEMAP = mapping.get_module_mapping(os.getcwd())
MODULEMAP, DUPLICATES = utils.eliminate_dict_listvalue_duplicates(MODULEMAP)
INTRAMODULE_DEPENDENCY_MAP = {}

if DUPLICATES:
  print("Error: Some files are included into multiple modules. These files "
        "had been removed from the mapping!", file=sys.stderr)
  print('\n'.join(DUPLICATES), file=sys.stderr)


def __all_files_in_folder(desc=""):
  """Wrapper function that returns a progressbar-decorated generator for
  all files in the current tree."""
  return tqdm(walk_folder(os.getcwd()),
              unit='files',
              desc=desc,
              total=len(list(walk_folder(os.getcwd()))),
              position=1)


# First look for header files and handle the include directives that a
# module fragment's header includes.
for file in __all_files_in_folder(desc="Ordering headers"):
  if not re.search(HEADER_FILE, file):
    continue

  content = None
  try:
    with codecs.open(file, 'r', encoding='utf-8', errors='replace') as f:
      content = f.read()
  except OSError as e:
    tqdm.write("Couldn't read file '%s': %s" % (file, e),
               file=sys.stderr)
    continue

  include.transform_includes_to_imports(file,
                                        content,
                                        MODULEMAP,
                                        INTRAMODULE_DEPENDENCY_MAP)

import json

for module in INTRAMODULE_DEPENDENCY_MAP.keys():
  try:
    topo = toposort.toposort(INTRAMODULE_DEPENDENCY_MAP[module])
    topo = list(topo)
    print("MODULE %s DEPENDENCIES" % module)
    topo = [list(x) for x in list(topo)]  # Convert sets to lists...
    print(json.dumps(topo, indent=2, sort_keys=False))
  except toposort.CircularDependencyError:
    print("Circular dependency in module '%s'." % module, file=sys.stderr)
    print("Ignoring for now...", file=sys.stderr)
    pass

#!/usr/bin/env python3

import codecs
import os
import re
import sys

from utils.progress_bar import tqdm
from ModulesTSMaker import *


HEADER_FILE = re.compile(r'\.(H(XX|PP|\+\+)?|h(xx|pp|\+\+)?|t(xx|pp|\+\+))$')

if not os.path.isfile("CMakeLists.txt"):
  print("Error: this script should be run from a source folder.",
        file=sys.stderr)
  sys.exit(2)


MODULEMAP, DUPLICATES = mapping.get_module_mapping(os.getcwd())
INTRAMODULE_DEPENDENCY_MAP = {}

if DUPLICATES:
  print("Error: Some files are included into multiple modules. These files "
        "had been removed from the mapping!", file=sys.stderr)
  print('\n'.join(DUPLICATES), file=sys.stderr)

# First look for header files and handle the include directives that a
# module fragment's header includes.
import time
headers = list(filter(HEADER_FILE.search, mapping.get_all_files(MODULEMAP)))
for file in tqdm(headers,
                 desc="Collecting includes",
                 unit='headers',
                 position=1):
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

  include.filter_imports_from_includes(file,
                                       content,
                                       MODULEMAP,
                                       INTRAMODULE_DEPENDENCY_MAP)

print("\n")

# Fix the headers in the module file so they are in a topological order.
# This ensures that intra-module dependencies in the order of the module's
# headers' inclusion are satisfied.
for module, dependencies in INTRAMODULE_DEPENDENCY_MAP.items():
  mapping.write_topological_order(MODULEMAP[module]['file'],
                                  MODULEMAP[module]['fragments'],
                                  HEADER_FILE,
                                  dependencies)

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
DEPENDENCY_MAP = mapping.DependencyMap(MODULEMAP)

if DUPLICATES:
  print("Error: Some files are included into multiple modules. These files "
        "had been removed from the mapping!", file=sys.stderr)
  print('\n'.join(DUPLICATES), file=sys.stderr)

# First look for header files and handle the include directives that a
# module fragment's header includes.
headers = list(filter(HEADER_FILE.search, MODULEMAP.get_all_fragments()))
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

  new_text = include.filter_imports_from_includes(
    file, content, MODULEMAP, DEPENDENCY_MAP)

print("\n")

# Check if the modules involve a circular
if not mapping.get_modules_circular_dependency(MODULEMAP, DEPENDENCY_MAP):
  print("Error: Modules contain circular dependencies on each other.",
        file=sys.stderr)
  sys.exit(1)

# Files can transitively and with the employment of header guards,
# recursively include each other, which is not a problem in normal C++,
# but for imports this must be evaded, as the files are put into a module
# wrapper, which should not include itself.
# However, for this module "wrapper" file to work, the includes of the
# module "fragments" (which are rewritten by this script) must be in
# a good order.
for module in tqdm(MODULEMAP,
                   desc="Sorting module includes",
                   unit='files'):
  files_in_module = MODULEMAP.get_fragment_list(module)
  headers_in_module = list(filter(HEADER_FILE.search, files_in_module))

  # By default, put every file known to be mapped into the module into
  # the list.
  intramodule_dependencies = dict(map(lambda x: (x, []),
                                      headers_in_module))
  # Then add the list of known dependencies from the previous built map.
  intramodule_dependencies.update(
    DEPENDENCY_MAP.get_intramodule_dependencies(module))

  mapping.write_topological_order(
    MODULEMAP.get_filename(module),
    files_in_module,
    HEADER_FILE,
    intramodule_dependencies)

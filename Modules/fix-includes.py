#!/usr/bin/env python3
"""
Return codes:
 0 - all good.
 1 - error, algorithm cannot run to completion.
 2 - configuration error.
"""

import codecs
import multiprocessing
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

# TODO: Revert this here, this is for testing the moving algorithm.
non_headers = set(MODULEMAP.get_all_fragments()) - set(headers)
print("SIZE BEFORE", len(list(MODULEMAP.get_all_fragments())))
for f in non_headers:
  MODULEMAP.remove_fragment(f)
print("SIZE AFTER", len(list(MODULEMAP.get_all_fragments())))

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

DEPENDENCY_MAP.synthesize_intermodule_imports()

print("\n")

# Check if the read module map contains circular dependencies that make the
# current module map infeasible, and try to resolve it.
# It is to be noted that this algorithm is finite, as worst case the system
# will fall apart to N distinct modules where N is the number of translation
# units -- unfortunately there was no improvement on modularisation made in
# this case...
all_files_to_move = dict()
module_map_infeasible = True

# TODO: There is some nondeterminism here, sometimes we exhaust the hash length
iteration_count = 0
with multiprocessing.Pool() as pool:
  while module_map_infeasible:
    iteration_count += 1
    print("=========->> Begin iteration %d trying to break cycles <<-========="
          % iteration_count)

    files_to_move = cycle_resolution.get_circular_dependency_resolution(
      pool, MODULEMAP, DEPENDENCY_MAP)

    if files_to_move is False:
      print("Error! The modules contain circular dependencies on each other "
            "which cannot be resolved automatically by splitting them.",
            file=sys.stderr)
      sys.exit(1)
    elif files_to_move is True:
      # If the resolution of the cycles is to do nothing, there are no issues
      # with the mapping anymore.
      module_map_infeasible = False
    else:
      # Alter the module map with the calculated moves, and try running the
      # iteration again.
      mapping.apply_file_moves(MODULEMAP, DEPENDENCY_MAP, files_to_move)
      all_files_to_move.update(files_to_move)

print("Module cycles broken up successfully.")
sys.exit(0)

# TODO: Actually move the files in "all_files_to_move".

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

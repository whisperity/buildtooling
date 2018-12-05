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

import utils
from utils.progress_bar import tqdm
from ModulesTSMaker import *

HEADER_FILE = re.compile(r'\.(H(XX|PP|\+\+)?|h(xx|pp|\+\+)?|t(xx|pp|\+\+))$')

# ---------------------- Sanity check invocation of tool ----------------------

if len(sys.argv) != 2:
  print("Error: Please specify a 'compile_commands.json' file for the "
        "project!", file=sys.stderr)
  sys.exit(2)

COMPILE_COMMAND_JSON = os.path.abspath(sys.argv[1])

START_FOLDER = os.getcwd()
if not os.path.isfile("CMakeLists.txt"):
  print("Error: this script should be run from a source folder.",
        file=sys.stderr)
  sys.exit(2)

SYMBOL_REWRITER_BINARY = 'SymbolRewriter'
success, _, _ = utils.call_process(SYMBOL_REWRITER_BINARY, ['--version'])
if not success:
  print("The 'SymbolRewriter' binary was not found in the PATH variable. "
        "This tool is shipped with the Python script and is a required "
        "dependency.",
        file=sys.stderr)
  sys.exit(2)

# ------------------------- Real execution begins now -------------------------

# In the end, after some heuristics, C++ files will be concatenated after one
# another into a "new TU" (of the module) which makes this new TU not compile
# as it is, because, for example, there are types in the anonymous namespace
# that conflict with a later file fragment.
success, _, output = utils.call_process(
  SYMBOL_REWRITER_BINARY,
  [os.path.dirname(COMPILE_COMMAND_JSON),
   str(multiprocessing.cpu_count())],
  cwd=START_FOLDER,
  stdout=None)
if not success:
  print("Error: The renaming of symbols in implementation files failed!",
        file=sys.stderr)
  print("The tool's output was:", file=sys.stderr)
  print(output, file=sys.stderr)
  sys.exit(1)

# The symbol rewriter binary creates outputs for files specifying in which file
# at what position a rename must be made so concatenated implementation files
# will work without name collisions that previously were not a problem when
# implementation files were different TUs.
symbol_rename_files = list(filter(lambda s: s.endswith("-symbols.txt"),
                                  utils.walk_folder(START_FOLDER)))
for directive_file in tqdm(symbol_rename_files,
                           desc="Renaming problematic symbols",
                           unit='file'):
  with open(directive_file, 'r') as directive_handle:
    if os.fstat(directive_handle.fileno()).st_size == 0:
      os.unlink(directive_file)
      continue

    for line in reversed(list(directive_handle)):
      # Parse the output of the directive file. A line is formatted like:
      #     main.cpp##1:1##Foo##main_Foo
      # The directives must be parsed in reverse order, because it could be
      # that the same line is to be modified multiple times, and a modification
      # earlier than the next in the line will make the column # for the given
      # line invalid.
      try:
        parts = line.strip().split('##')
        filename = parts[0]
        line, col = parts[1].split(':')
        from_str = parts[2]
        to_str = parts[3]

        success = utils.replace_at_position(filename,
                                            int(line), int(col),
                                            from_str, to_str)
        if not success:
          tqdm.write("Replacement failed for directive: %s" % line,
                     file=sys.stderr)
      except IndexError:
        tqdm.write("Invalid directive in file:\n\t%s" % line, file=sys.stderr)
        continue


# Get the current pre-existing module mapping for the project.
MODULEMAP, DUPLICATES = mapping.get_module_mapping(START_FOLDER)
DEPENDENCY_MAP = mapping.DependencyMap(MODULEMAP)

if DUPLICATES:
  print("Error: Some files are included into multiple modules. These files "
        "had been removed from the mapping!", file=sys.stderr)
  print('\n'.join(DUPLICATES), file=sys.stderr)


# The SYMBOL_REWRITER_BINARY also emits the knowledge about what file
# implements symbols from what other file. This has to be added to the
# algorithm's knowledge, as Module files (CPPMs) have to contain *both*
# interface and implementation.
header_implements_files = list(filter(lambda s: s.endswith("-implements.txt"),
                                      utils.walk_folder(START_FOLDER)))
for directive_file in tqdm(header_implements_files,
                           desc="Finding implemented headers",
                           unit='file'):
  with open(directive_file, 'r') as directive_handle:
    if os.fstat(directive_handle.fileno()).st_size == 0:
      os.unlink(directive_file)
      continue

    for line in reversed(list(directive_handle)):
      # Parse the output of the directive file. A line is formatted like:
      #     main.cpp##something.h
      try:
        parts = line.strip().split('##')
        implementee = utils.strip_folder(START_FOLDER, parts[0])
        implemented = utils.strip_folder(START_FOLDER, parts[1])
        DEPENDENCY_MAP.add_dependency(implementee, implemented, 'implements')
      except ValueError as ve:
        tqdm.write("Implements relation failed, because: %s" % str(ve),
                   file=sys.stderr)
      except IndexError:
        tqdm.write("Invalid directive in file:\n\t%s" % line, file=sys.stderr)
        continue


# The implements relations could make the whole setup insane when a "header"'s
# contents is implemented by multiple translation units belonging to different
# modules. Because the latter algorithm only *splits* modules apart, if the
# initial mapping is insane, the calculations don't need to be made, as further
# splits won't fix the input.
insanity = mapping.get_dependency_map_implementation_insanity(DEPENDENCY_MAP)
if insanity:
  print("Error: The initial input of module-assignments given to the "
        "algorithm is insane. At least one interface (\"header\") file is "
        "implemented by translation units assigned to multiple different "
        "modules.", file=sys.stderr)

  for implemented, module_and_files in sorted(insanity.items()):
    module_of_implemented = next(
      MODULEMAP.get_modules_for_fragment(implemented),
      None)
    print("Symbols of file '%s' in module %s (%s) is implemented by:"
          % (implemented,
             module_of_implemented,
             MODULEMAP.get_filename(module_of_implemented)),
          file=sys.stderr)
    for module, file_list in sorted(module_and_files.items()):
      print("    in module '%s' (%s):"
            % (module, MODULEMAP.get_filename(module)), file=sys.stderr)
      for file in sorted(file_list):
        print("        %s" % file, file=sys.stderr)

  print("Please review and change your code, or remove the problematic "
        "interface files from the assignment, reducing them to pure headers.",
        file=sys.stderr)
  sys.exit(1)


# First look for header files and handle the include directives that a
# module fragment's header includes.
headers = list(filter(HEADER_FILE.search, MODULEMAP.get_all_fragments()))
for file in tqdm(headers,
                 desc="Collecting includes",
                 unit='header',
                 position=1):
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

  # TODO: What to do with this 'new_text'? We should write it to the FS...

DEPENDENCY_MAP.synthesize_intermodule_imports()
print('\n')


# Check if the read module map contains circular dependencies that make the
# current module map infeasible, and try to resolve it.
# It is to be noted that this algorithm is finite, as worst case the system
# will fall apart to N distinct modules where N is the number of translation
# units -- unfortunately there was no improvement on modularisation made in
# this case...
iteration_count = 1
with multiprocessing.Pool() as pool:
  while True:
    print("========->> Begin iteration %d trying to break cycles.. <<-========"
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
      print("Nothing to do.")
      break
    else:
      # Alter the module map with the calculated moves, and try running the
      # iteration again.
      mapping.apply_file_moves(MODULEMAP, DEPENDENCY_MAP, files_to_move)

    iteration_count += 1


# Headers have been moved at this point, but only the module map in memory has
# changed, not the original source code. The next step is to move the
# non-header files alongside with the headers, for the types they implement
# (as modules need to contain interface and implementation in the same "TU").
implementation_files_to_move = dict()
for module in tqdm(sorted(MODULEMAP),
                   desc="Organising implementation files",
                   unit='module'):
  files_in_module = MODULEMAP.get_fragment_list(module)

  for header in filter(HEADER_FILE.search, files_in_module):
    dependee_set = DEPENDENCY_MAP.get_dependees(header)
    for dependee, kind in dependee_set:
      if kind != 'implements':
        continue

      modules_of_dependee = list(MODULEMAP.get_modules_for_fragment(dependee))
      if modules_of_dependee[0] != module:
        implementation_files_to_move[dependee] = module

mapping.apply_file_moves(MODULEMAP,
                         DEPENDENCY_MAP,
                         implementation_files_to_move)


# After (and if successfully) the modules has been split up, commit the changes
# to the file system for the upcoming operations.
if iteration_count > 1:
  print("Module cycles broken up successfully.")
  mapping.write_module_mapping(START_FOLDER, MODULEMAP)
  print('\n')


# Files can transitively and with the employment of header guards,
# recursively include each other, which is not a problem in normal C++,
# but for imports this must be evaded, as the files are put into a module
# wrapper, which should not include itself.
# However, for this module "wrapper" file to work, the includes of the
# module "fragments" (which are rewritten by this script) must be in
# a good order.
topological_success = True
for module in tqdm(sorted(MODULEMAP),
                   desc="Sorting headers",
                   unit='module'):
  files_in_module = MODULEMAP.get_fragment_list(module)
  headers_in_module = filter(HEADER_FILE.search, files_in_module)

  # By default, put every file known to be mapped into the module into
  # the list. (But they are not marked to have any dependencies.)
  intramodule_dependencies = dict(map(lambda x: (x, []),
                                      headers_in_module))
  # Then add the list of known dependencies from the previous built map.
  for dependee_module, dep_pair in \
        DEPENDENCY_MAP.get_intramodule_dependencies(module).items():
    dep_list = list()
    for tupl in dep_pair:
      # Remove the "kind" attribute from the dependency graph for this.
      filename, kind = tupl
      if kind == 'uses' and HEADER_FILE.match(filename):
        dep_list.append(filename)
    if dep_list:
      # Only save the dependency into this dict if the file partook in any
      # uses-dependency relation.
      intramodule_dependencies[dependee_module] = sorted(dep_list)

  topological_success = topological_success and \
                        mapping.write_topological_order(
                          MODULEMAP.get_filename(module),
                          HEADER_FILE,
                          intramodule_dependencies)

if not topological_success:
  print("Error: one of more module files' interface (header) part could not "
        "have been sorted properly.",
        file=sys.stderr)
  sys.exit(1)

#!/usr/bin/env python3
"""
Return codes:
 0 - all good.
 1 - error, algorithm cannot run to completion.
 2 - configuration error.
"""

import os
import re
import sys

import utils
from passes import PassLoader

PassLoader.register_global(
  'HEADER_FILE_REGEX',
  re.compile(r'\.(H(XX|PP|\+\+)?|h(xx|pp|\+\+)?|t(xx|pp|\+\+))$'))

# ---------------------- Sanity check invocation of tool ----------------------

if len(sys.argv) != 3:
  print("Error: Please specify a 'compile_commands.json' file for the "
        "project! (As 1st argument.)", file=sys.stderr)
  print("Error: Please specify the 'Modules.cmake' deploy's location for the "
        "project! (As 2nd argument.)", file=sys.stderr)
  sys.exit(2)

COMPILE_COMMAND_JSON = os.path.abspath(sys.argv[1])
PassLoader.register_global('COMPILE_COMMAND_JSON', COMPILE_COMMAND_JSON)

MODULES_CMAKE_SCRIPT = os.path.abspath(sys.argv[2])
PassLoader.register_global('MODULES_CMAKE_SCRIPT', MODULES_CMAKE_SCRIPT)

START_FOLDER = os.getcwd()
PassLoader.register_global('START_FOLDER', START_FOLDER)
if not os.path.isfile("CMakeLists.txt"):
  print("Error: this script should be run from a source folder.",
        file=sys.stderr)
  sys.exit(2)

SYMBOL_REWRITER_BINARY = 'SymbolRewriter'
PassLoader.register_global('SYMBOL_REWRITER_BINARY', SYMBOL_REWRITER_BINARY)
success, _, _ = utils.call_process(SYMBOL_REWRITER_BINARY, ['--version'])
if not success:
  print("The 'SymbolRewriter' binary was not found in the PATH variable. "
        "This tool is shipped with the Python script and is a required "
        "dependency.",
        file=sys.stderr)
  sys.exit(2)

# ------------------------- Real execution begins now -------------------------

# PassLoader.execute_pass('execute_symbol_rewriter')

# Load the necessary knowledge about the project.
MODULE_MAP, DEPENDENCY_MAP = \
  PassLoader.execute_pass('load_module_mapping')
PassLoader.register_global('MODULE_MAP', MODULE_MAP)
PassLoader.register_global('DEPENDENCY_MAP', DEPENDENCY_MAP)

PassLoader.execute_pass('load_implements_relations')

# Fetch the dependencies from the headers only.
PassLoader.register_global(
  'FILTER_FILE_REGEX',
  PassLoader.get('HEADER_FILE_REGEX'))
PassLoader.execute_pass('fetch_dependency_includes')
PassLoader.register_global('FILTER_FILE_REGEX', None)

# Execute the passes of the algorithm and try to solve modularisation.
PassLoader.execute_pass('solve_potential_module_import_cycles')
PassLoader.execute_pass('move_implementation_files_to_new_modules')
PassLoader.execute_pass('rename_conflicting_symbols')

# After the types had been broken up, implementation files can still have some
# dependent headers.
PassLoader.register_global(
  'FILTER_FILE_REGEX',
  re.compile(r'\.(C(XX|PP|\+\+)?|c(xx|pp|\+\+)?|i(xx|pp|\+\+))$'))
PassLoader.execute_pass('fetch_dependency_includes')
PassLoader.register_global('FILTER_FILE_REGEX', None)

PassLoader.execute_pass('join_implementation_cycles')

# Save the algorithm's output.
PassLoader.execute_pass('write_module_files')
PassLoader.execute_pass('emit_cmake_module_directives')

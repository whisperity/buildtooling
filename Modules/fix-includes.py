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
from stages import ExecutionStepWrapper

ExecutionStepWrapper.register_global(
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
ExecutionStepWrapper.register_global('COMPILE_COMMAND_JSON',
                                     COMPILE_COMMAND_JSON)

MODULES_CMAKE_SCRIPT = os.path.abspath(sys.argv[2])
ExecutionStepWrapper.register_global('MODULES_CMAKE_SCRIPT',
                                     MODULES_CMAKE_SCRIPT)

START_FOLDER = os.getcwd()
ExecutionStepWrapper.register_global('START_FOLDER',
                                     START_FOLDER)
if not os.path.isfile("CMakeLists.txt"):
  print("Error: this script should be run from a source folder.",
        file=sys.stderr)
  sys.exit(2)

SYMBOL_REWRITER_BINARY = 'SymbolRewriter'
ExecutionStepWrapper.register_global('SYMBOL_REWRITER_BINARY',
                                     SYMBOL_REWRITER_BINARY)
success, _, _ = utils.call_process(SYMBOL_REWRITER_BINARY, ['--version'])
if not success:
  print("The 'SymbolRewriter' binary was not found in the PATH variable. "
        "This tool is shipped with the Python script and is a required "
        "dependency.",
        file=sys.stderr)
  sys.exit(2)

# ------------------------- Real execution begins now -------------------------

ExecutionStepWrapper.execute_stage('execute_symbol_rewriter')

# Load the necessary knowledge about the project.
MODULE_MAP, DEPENDENCY_MAP = \
  ExecutionStepWrapper.execute_stage('load_module_mapping')
ExecutionStepWrapper.register_global('MODULE_MAP', MODULE_MAP)
ExecutionStepWrapper.register_global('DEPENDENCY_MAP', DEPENDENCY_MAP)

ExecutionStepWrapper.execute_stage('load_implements_relations')

# Fetch the dependencies from the headers only.
ExecutionStepWrapper.register_global(
  'FILTER_FILE_REGEX', ExecutionStepWrapper.get('HEADER_FILE_REGEX'))
ExecutionStepWrapper.execute_stage('fetch_dependency_includes')
ExecutionStepWrapper.register_global('FILTER_FILE_REGEX', None)

# Execute the stages of the algorithm and try to solve modularisation.
ExecutionStepWrapper.execute_stage('solve_potential_module_import_cycles')
ExecutionStepWrapper.execute_stage('move_implementation_files_to_new_modules')
ExecutionStepWrapper.execute_stage('rename_conflicting_symbols')

# After the types had been broken up, implementation files can still have some
# dependent headers.
ExecutionStepWrapper.register_global(
  'FILTER_FILE_REGEX',
  re.compile(r'\.(C(XX|PP|\+\+)?|c(xx|pp|\+\+)?|i(xx|pp|\+\+))$'))
ExecutionStepWrapper.execute_stage('fetch_dependency_includes')
ExecutionStepWrapper.register_global('FILTER_FILE_REGEX', None)

ExecutionStepWrapper.execute_stage('join_implementation_cycles')

# Save the algorithm's output.
ExecutionStepWrapper.execute_stage('write_module_files')
ExecutionStepWrapper.execute_stage('emit_cmake_module_directives')

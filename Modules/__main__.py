#!/usr/bin/env python3
"""
Return codes:
 0 - all good.
 1 - error, algorithm cannot run to completion.
 2 - configuration error.
"""

import argparse
import datetime
import os
import re
import sys
import time
from multiprocessing import cpu_count

import utils
from utils.graph import nx
from utils.graph_visualisation import load_for as load_graphviz
from passes import PassLoader

# ------------------- Set up the command-line configuration -------------------

# TODO: Macros can bleed out of the buffer if files are concatenated. While
# TODO: this isn't a problem if a macro is defined only in a TU and redefined
# TODO: in another TU (compiler will give a warning on this), subtle header
# TODO: macro bleedouts MIGHT change behaviour of the program massively.
#
# TODO: It should be added to either ModuleMake or to SymbolAnaliser to find
# TODO: these macros and report an error if their meanings would change down
# TODO: the line, or rename them...

PARSER = argparse.ArgumentParser(
  prog='automodules',
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Attempt to perform an automatic modularisation of the given "
              "C++ project. This automatic modularisation changes input files "
              "and build relations, but does not - apart from simple renames "
              "- touch the actual source code.",
  epilog="There are certain steps that must be made BEFORE this tool can "
         "successfully run. Such actions include preparing the build system "
         "of the affected project and generating a build configuration of the "
         "non-modularised build is necessary.")

PARSER.add_argument('compilation_database',
                    type=str,
                    help="Path to the compilation database of the project.")

PARSER.add_argument('modulescript',
                    type=str,
                    help="Path to the location where the Module Maker's CMake "
                         "extension could should be unpacked to. THIS FILE "
                         "WILL BE OVERWRITTEN!")

PARSER.add_argument('--symbol-analyser',
                    type=str,
                    metavar='SymbolAnalyser',
                    default='SymbolAnalyser',
                    help="Override path to the 'SymbolAnalyser' binary which "
                         "is used to analyse the project. This binary is "
                         "mandatory for success and is shipped with the "
                         "Python driver. (The binary is searched in the PATH "
                         "environment variable if not overridden.)")

PARSER.add_argument('--force-reanalysis',
                    action='store_true',
                    help="SymbolAnalyser is not ran twice for the same "
                         "project as analysis takes O(build time) to complete."
                         " Specifying this flag will re-run the analysis even "
                         "if the marker for successful analysis is found.")

PARSER.add_argument('-j', '--jobs',
                    type=int,
                    metavar='num_threads',
                    default=0,
                    help="Override the number of threads allowed to be used "
                         "for executing analysis and operations. (Certain "
                         "parts of the executed algorithm can not be run in "
                         "parallel!) A default value of '0' indicates to use "
                         "as many threads as available.")

PARSER.add_argument('-n', '--dry-run',
                    action='store_true',
                    help="Execute the algorithm but stop before any "
                         "modifications would be made to the project files. "
                         "(Note: This flag does NOT affect the separate "
                         "'SymbolAnalyser' tool's execution.)")

PARSER.add_argument('--profile',
                    action='store_true',
                    help="Show profiling information at the end of execution "
                         "about how much each individual pass' execution "
                         "took.")

GRAPHS = PARSER.add_argument_group(
  'graph visualisation arguments',
  """Visualise the inner state of the algorithm by plotting the graphs in a
  graphical interface format. Using this option WILL slow down execution and
  block on each step until the graph window is closed.
  (Due to this, '--profile' information is worthless in this mode.)
  If '--jobs' is more than 1, each thread will most likely block independently!
  Specifying these arguments requires MatPlotLib, GraphViz and TkInter to be
  installed on the system.""")

GRAPHS.add_argument('--visualise-dependencies',
                    action='store_true',
                    help="Visualize the dependency graph between program code "
                         "files in the project.")

GRAPHS.add_argument('--visualise-cuts',
                    action='store_true',
                    help="Visualize the cuts performed on the "
                         "module-to-module level, due to cycles between "
                         "interface dependencies.")

GRAPHS.add_argument('--visualise-joins',
                    action='store_true',
                    help="Visualize the joins performed on the "
                         "module-to-module level, due to cycles introduced "
                         "by implementatioon code bringing in dependencies "
                         "to other interfaces.")

CONFIGS = PARSER.add_argument_group('fine-tune configuration arguments')


def _regex_type(s):
  try:
    return re.compile(s)
  except Exception:
    raise argparse.ArgumentTypeError


CONFIGS.add_argument(
  '--header-regex',
  type=_regex_type,
  metavar='REGEX',
  default=r'\.(H(H|XX|PP|\+\+)?|h(h|xx|pp|\+\+)?|t(t|xx|pp|\+\+))$',
  help="Regular exception to match for the extension of HEADER / INTERFACE "
       "files of the project. By default matches hh, hpp/tpp and their xx/++ "
       "variants.")

CONFIGS.add_argument(
  '--source-file-regex',
  type=_regex_type,
  metavar='REGEX',
  default=r'\.(C(C|XX|PP|\+\+)?|c(c|xx|pp|\+\+)?|i(i|xx|pp|\+\+))$',
  help="Regular exception to match for the extension of SOURCE / "
       "IMPLEMENTATION files of the project. By default matches cc, cpp/ipp "
       "and their xx/++ variants.")

CONFIGS.add_argument("--module-split-pingpong-threshold",
                     type=int,
                     default=8,
                     metavar="ITERATIONS",
                     help="The size of the sliding window of cycles in the "
                          "'split circular module interfaces' step are "
                          "temporarily collected. If in at most this many "
                          "iterations the same cycle is \"rediscovered\" "
                          "then the algorithm is terminated with an error.")

LOGGING = PARSER.add_argument_group('output verbosity arguments')

LOGGING.add_argument('--hide-compiler',
                     action='store_true',
                     help="Hide the output (warnings and errors) of the "
                          "compiler in the analysis phase.")

LOGGING.add_argument('--hide-nonessential',
                     action='store_true',
                     help="Hide warning of the tool that are not essential "
                          "and in many cases can safely be ignored. These "
                          "warnings are sometimes normal, sometimes expected "
                          "depending on how the initial input is configured.")

LOGGING.add_argument('--verbose',
                     action='store_true',
                     help="Show more verbose status messages about the steps "
                          "the algorithm took, its progress, etc.")

ARGS = PARSER.parse_args()

# ---------------------- Sanity check invocation of tool ----------------------

PassLoader.register_global('COMPILE_COMMANDS_JSON',
                           os.path.abspath(ARGS.compilation_database))

PassLoader.register_global('MODULES_CMAKE_SCRIPT',
                           os.path.abspath(ARGS.modulescript))

PassLoader.register_global('START_FOLDER', os.getcwd())
if not os.path.isfile("CMakeLists.txt"):
  print("Error: this script should be run from the source tree.",
        file=sys.stderr)
  sys.exit(2)

SYMBOL_ANALYSER_BINARY = ARGS.symbol_analyser
PassLoader.register_global('SYMBOL_ANALYSER_BINARY', SYMBOL_ANALYSER_BINARY)
success, _, _ = utils.call_process(SYMBOL_ANALYSER_BINARY, ['--version'])
if not success:
  print("The 'SymbolAnalyser' binary was not found in the PATH environment "
        "directories. This tool is shipped with the Python script and is a "
        "required dependency.\nBuild the tool and add its output folder to "
        "PATH, or specify '--symbol-analyser' manually at invocation.",
        file=sys.stderr)
  sys.exit(2)

# Set up the logging configuration of the user.
utils.logging.set_configuration('compiler', not ARGS.hide_compiler)
utils.logging.set_configuration('normal', not ARGS.hide_nonessential)
utils.logging.set_configuration('verbose', ARGS.verbose)

# Set up how many threads can be run.
if ARGS.jobs <= 0:
  ARGS.jobs = cpu_count()
utils.logging.verbose("Using '%d' thread(s)..." % ARGS.jobs)
PassLoader.register_global('THREAD_COUNT', ARGS.jobs)

# Load the visualiser algorithm into the interpreter.
load_graphviz('dependencies', ARGS.visualise_dependencies)
load_graphviz('cuts', ARGS.visualise_cuts)
load_graphviz('joins', ARGS.visualise_joins)

# ------------------------- Real execution begins now -------------------------

START_AT = time.time()

# Perform an analysis on the symbols and the project structure to know what
# has to be touched.
PassLoader.register_global('ALWAYS_DO_ANALYSIS', ARGS.force_reanalysis)
PassLoader.execute_pass('execute_symbol_analyser')

INCLUDE_PATHS = PassLoader.execute_pass('parse_include_paths_from_cdb')
PassLoader.register_global('INCLUDE_PATHS', INCLUDE_PATHS)

# Load the necessary knowledge about the project.
MODULE_MAP, DEPENDENCY_MAP = \
  PassLoader.execute_pass('load_module_mapping')
PassLoader.register_global('MODULE_MAP', MODULE_MAP)
PassLoader.register_global('DEPENDENCY_MAP', DEPENDENCY_MAP)

PassLoader.register_global('REMOVE_LINES_FROM_FILES', dict())
PassLoader.register_global('EXTERNAL_INCLUDE_GRAPH', nx.DiGraph())

PassLoader.execute_pass('load_implements_relations')
DEFINITIONS, FORWARD_DECLARATIONS = \
  PassLoader.execute_pass('load_module_affected_symbol_table')
PassLoader.register_global('DEFINITIONS', DEFINITIONS)
PassLoader.register_global('FORWARD_DECLARATIONS', FORWARD_DECLARATIONS)

# Fetch the dependencies from the headers only.
PassLoader.register_global('HEADER_FILE_REGEX', ARGS.header_regex)
PassLoader.register_global('FILTER_FILE_REGEX',
                           PassLoader.get('HEADER_FILE_REGEX'))
PassLoader.execute_pass('fetch_dependency_includes')
PassLoader.register_global('FILTER_FILE_REGEX', None)

# Execute the passes of the algorithm and try to solve modularisation.
PassLoader.register_global('MODULE_SPLIT_PINGPONG_THRESHOLD',
                           ARGS.module_split_pingpong_threshold)
PassLoader.execute_pass('solve_potential_module_import_cycles')
PassLoader.execute_pass('move_implementation_files_to_new_modules')

# After the types had been broken up, implementation files can still have some
# dependent headers.
PassLoader.register_global('FILTER_FILE_REGEX', ARGS.source_file_regex)
PassLoader.execute_pass('fetch_dependency_includes')
PassLoader.register_global('FILTER_FILE_REGEX', None)

PassLoader.execute_pass('join_implementation_cycles')
PassLoader.execute_pass('move_forward_declarations_to_defining_module')

if not ARGS.dry_run:
  # Save the algorithm's output.
  PassLoader.execute_pass('rename_conflicting_symbols')
  NON_TOPOLOGICAL_FILES = PassLoader.execute_pass('write_module_files')
  PassLoader.register_global('NON_TOPOLOGICAL_FILES', NON_TOPOLOGICAL_FILES)
  PassLoader.execute_pass('remove_lines_from_source')
  PassLoader.execute_pass('emit_cmake_module_directives')
else:
  utils.logging.normal("\n\n'--dry-run' was specified: not writing output.")

END_AT = time.time()

# --------------------------------- Profiling ---------------------------------
# Load the visualiser algorithm into the interpreter.
if ARGS.profile and (ARGS.visualise_dependencies or
                     ARGS.visualise_cuts or
                     ARGS.visualise_joins):
  print("Profiling information ignored as graph visualisations happened.")
elif ARGS.profile:
  print("====================================================================")
  print("Execution started at %s.\n"
        % datetime.datetime.fromtimestamp(START_AT)
        .strftime(r'%Y-%m-%d %H:%M:%S.%f'))
  for i, tupl in enumerate(PassLoader.timing_informations):
    pass_name, start, end = tupl

    start_human = datetime.datetime.fromtimestamp(start).strftime(
      r'%Y-%m-%d %H:%M:%S.%f')
    end_human = datetime.datetime.fromtimestamp(end).strftime(
      r'%Y-%m-%d %H:%M:%S.%f')
    delta = datetime.timedelta(seconds=end - start)
    print("#%d. Pass %s: started at %s, ended at %s,"
          "\n%stook %s"
          % (i, pass_name, start_human, end_human,
             ' ' * len("#%d. Pass " % i), delta))

  print("\nExecution ended at %s."
        % datetime.datetime.fromtimestamp(END_AT)
        .strftime(r'%Y-%m-%d %H:%M:%S.%f'))
  print("Total execution took %s wall time."
        % datetime.timedelta(seconds=END_AT - START_AT))

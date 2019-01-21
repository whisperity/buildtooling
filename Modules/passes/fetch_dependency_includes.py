import codecs
import os
import sys
from operator import itemgetter

from ModulesTSMaker import include
import utils
from utils.progress_bar import tqdm

PASS_NAME = "Fetch dependency \"#include\"s from files"


def _recurse_includes(start_folder,
                      module_map,
                      include_graph,
                      file,
                      known_external_includes=None):
  """
  Perform a recursive descent (depth-first search) on the includes of the given
  file. The external (not in the module map) include walks are collected and
  added to the graph.

  :param start_folder: The folder where the script was started.
  :param module_map: The module map populated with project information.
  :param include_graph: A directed graph that will have nodes and edges related
  to the descents added to. The nodes are extended with the attributes
  'external' and 'modules' - external is True if the file doesn't belong to any
  modules, otherwise the 'modules' attribute shows which modules the file
  belongs to - this is a collection, but is supposed to contain only one
  element.
  :param file: The file to open and continue traversing. This file path is
  attempted to be expanded if not found verbatim.
  :param known_external_includes: The list of external include FILES (not
  directives) to traverse into from :param file:. If this is not 'None', only
  these directives are used, otherwise :param file: is actually read from the
  disk and parsed.

  :note: If :param known_external_includes: is specified, the file is NOT read
  and it is NOT checked if file truly includes a "known" include. Use this
  option with caution.
  """
  if not os.path.isfile(file):
    file = os.path.join(start_folder, file)
  if not os.path.isfile(file):
    return False
  if file in include_graph:
    # Don't load the contents of a file multiple times.
    return file

  if known_external_includes is None:
    try:
      with codecs.open(file, 'r',
                       encoding='utf-8', errors='replace') as f:
        known_external_includes = include.get_included_files(f.read())
    except OSError as e:
      print("OSerror on file '%s': %s" % (file, str(e)),
            file=sys.stderr)
      return False

  for next_include in known_external_includes:
    include_found_at = _recurse_includes(start_folder,
                                         module_map,
                                         include_graph,
                                         next_include)
    if not include_found_at:
      continue

    # Add the include dependency to the external include map if *either*
    # sides of the inclusion is outside the to-modularise input. This is
    # needed because if A -> B -> C -> D and B and C are outside of
    # modules, the include sorter needs to know that A must be sorted
    # before D transitively.
    modules_of_current = list(
      module_map.get_modules_for_fragment(file))
    modules_of_next_included = list(
      module_map.get_modules_for_fragment(include_found_at))
    if file not in include_graph.nodes:
      include_graph.add_node(file,
                             external=not modules_of_current,
                             modules=modules_of_current)
    if include_found_at not in include_graph.nodes:
      include_graph.add_node(include_found_at,
                             external=not modules_of_next_included,
                             modules=modules_of_next_included)

    include_graph.add_edge(file, include_found_at)

  return file


def main(START_FOLDER,
         MODULE_MAP,
         DEPENDENCY_MAP,
         FILTER_FILE_REGEX,
         REMOVE_LINES_FROM_FILES,
         EXTERNAL_INCLUDE_GRAPH):
  # Handle removing #include directives from files matching the given RegEx and
  # adding them as module imports instead.
  files = list(filter(FILTER_FILE_REGEX.search,
                      MODULE_MAP.get_all_fragments()))
  for file in tqdm(files,
                   desc="Collecting includes",
                   unit='file',
                   position=1):
    try:
      with codecs.open(file, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    except OSError as e:
      tqdm.write("Couldn't read file '%s': %s" % (file, e),
                 file=sys.stderr)
      continue

    lines_to_remove_from_file, lines_to_keep = \
      include.filter_imports_from_includes(file,
                                           content,
                                           MODULE_MAP,
                                           DEPENDENCY_MAP)

    if not lines_to_remove_from_file:
      continue
    utils.append_to_dict_element(REMOVE_LINES_FROM_FILES,
                                 file,
                                 lines_to_remove_from_file)

    if not lines_to_keep:
      continue

    # Files can contain includes which are not in the module map. However, a
    # file outside the module mapping can include a file in the module system.
    _recurse_includes(START_FOLDER,
                      MODULE_MAP,
                      EXTERNAL_INCLUDE_GRAPH,
                      file,
                      # Start the original recursion only on the "known"
                      # includes that did not match inside the module map.
                      known_external_includes=list(
                        map(include.directive_to_filename,
                            map(itemgetter(1), lines_to_keep))))

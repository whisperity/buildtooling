import sys

try:
  import networkx as nx
except ImportError as e:
  print("Error! A dependency of this tool could not be satisfied. Please "
        "install the following Python package via 'pip' either to the "
        "system, or preferably create a virtualenv.")
  raise

from ModulesTSMaker import mapping
from utils import logging
from utils.progress_bar import tqdm


DESCRIPTION = "Join modules together based on forward declarations' coupling"


def main(MODULE_MAP,
         DEPENDENCY_MAP,
         DEFINITIONS,
         FORWARD_DECLARATIONS):
  """
  Forward declarations are to be handled differently when a project is upgraded
  to the Modules TS system. If a class is forward declared in a module other
  than where it is defined, the forward declaration can end up constituting a
  definition and thus a collision with the actual definition. For this, forward
  declarations must be cleaned from the files where the definition is in
  another module.

  This pass merges modules further based on forward declarations, as they
  represent a bond that the user (because eventually a forward declaration
  in a header will be (in the vast majority of cases) used in the
  implementation file.
  """
  definitions_to_modules = dict()
  for symbol, file_list in DEFINITIONS.items():
    definitions_to_modules[symbol] = set()
    for file in file_list:
      for modules_for_definition in MODULE_MAP.get_modules_for_fragment(file):
        definitions_to_modules[symbol].add(modules_for_definition)

  # Represent the merges as components of a graph, because it's less
  # implementation for us this way.
  module_merges = nx.Graph({m: [] for m in MODULE_MAP})

  for file in tqdm(FORWARD_DECLARATIONS,
                   desc="Moving forward declarations",
                   unit='file'):
    modules_of_fwding_file = set(MODULE_MAP.get_modules_for_fragment(file))
    if not modules_of_fwding_file:
      # If a file does not belong to a module, ignore it.
      continue
    if len(modules_of_fwding_file) > 1:
      logging.essential("ERROR: Forward declaring file %s belongs to multiple "
                        "modules: %s. The forward declaration cannot be used "
                        "as a link of module merging."
                        % (file, ', '.join(modules_of_fwding_file)),
                        file=sys.stderr)
      sys.exit(1)
    modules_of_fwding_file = list(modules_of_fwding_file)

    for line, symbol in FORWARD_DECLARATIONS[file]:
      modules_of_definition = definitions_to_modules.get(symbol, set())
      if not modules_of_definition:
        logging.verbose("Symbol '%s' forward declared in %s was not found in "
                        "the loaded definition symbol table."
                        % (symbol, file),
                        file=sys.stderr)
        continue
      if len(modules_of_definition) > 1:
        logging.essential("ERROR: Symbol '%s' forward declared in file %s is "
                          "defined in multiple modules: %s (by files %s). The "
                          "forward declaration cannot be used as a link of "
                          "module merging."
                          % (symbol, file,
                             ', '.join(modules_of_definition),
                             ', '.join(DEFINITIONS[symbol])),
                          file=sys.stderr)
        sys.exit(1)
      modules_of_definition = list(modules_of_definition)

      # If a forward declaration to its definition links two modules, create
      # the link.
      logging.verbose("Symbol '%s' forward declared in file %s in module %s "
                      "refers to definition in %s in module %s. Setting up "
                      "modules for merge."
                      % (symbol, file, modules_of_fwding_file[0],
                         list(DEFINITIONS[symbol])[0],
                         modules_of_definition[0]))
      module_merges.add_edge(modules_of_fwding_file[0],
                             modules_of_definition[0])

  for comp in filter(lambda c: len(c) > 1,
                     nx.connected_components(module_merges)):
    logging.verbose("Merging modules due to forward declaration "
                    "co-dependencies: %s." % ', '.join(sorted(comp)))
    file_moves = dict()
    dummy_name = 'fwd_merged_' + mapping.get_new_module_name(MODULE_MAP, comp)

    for module in comp:
      for file in MODULE_MAP.get_fragment_list(module):
        file_moves[file] = dummy_name

    mapping.apply_file_moves(MODULE_MAP, DEPENDENCY_MAP, file_moves)

  mapping.fix_module_names(MODULE_MAP, DEPENDENCY_MAP)
  logging.essential(
    "-------- Final count of files in each modules after merging --------")
  for module in sorted(MODULE_MAP):
    length = len(MODULE_MAP.get_fragment_list(module))
    if length:
      logging.essential("     Module %s: %d" % (module, length))

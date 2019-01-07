import sys

from ModulesTSMaker import mapping
import utils
from utils.progress_bar import tqdm


PASS_NAME = "Clean unneeded forward declarations from the source files."


def main(MODULE_MAP,
         DEFINITIONS,
         FORWARD_DECLARATIONS,
         REMOVE_LINES_FROM_FILES):
  """
  Forward declarations are to be handled differently when a project is upgraded
  to the Modules TS system. If a class is forward declared in a module other
  than where it is defined, the forward declaration can end up constituting a
  definition and thus a collision with the actual definition. For this, forward
  declarations must be cleaned from the files where the definition is in
  another module - chances are that the implementation code actually uses the
  defined type and thus a "uses" relation was discovered earlier.
  """
  definitions_to_modules = dict()
  for symbol, file_list in DEFINITIONS.items():
    definitions_to_modules[symbol] = set()
    for file in file_list:
      print("checking file ", file)
      for modules_for_definition in MODULE_MAP.get_modules_for_fragment(file):
        definitions_to_modules[symbol].add(modules_for_definition)

  for file in tqdm(FORWARD_DECLARATIONS,
                   desc="Cleaning forward declarations",
                   unit='file'):
    # TODO: This doesn't work it removes forwards from the module that is
    # TODO: imported to another and the imported module just breaks.

    modules_of_fwding_file = set(MODULE_MAP.get_modules_for_fragment(file))
    file_remove_list = REMOVE_LINES_FROM_FILES.get(file, list())
    if not file_remove_list:
      REMOVE_LINES_FROM_FILES[file] = file_remove_list

    # Check which forward declaration points to a symbol defined in another
    # module. Only remove these, as removing intramodule forwards might break
    # the code at build.
    for line, symbol in FORWARD_DECLARATIONS[file]:
      modules_of_definition = definitions_to_modules.get(symbol, set())
      # if not modules_of_definition:
      #   tqdm.write("In file '%s' the symbol '%s' forward declared without "
      #              "definition. Is the mapping bad?" % (file, symbol),
      #              file=sys.stderr)

      if not (modules_of_fwding_file & modules_of_definition):
        # Mark the forward declaration for removal if the declaration and the
        # definition are not in the same module.
        file_remove_list.append((line - 1, symbol))

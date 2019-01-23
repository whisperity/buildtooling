import sys

import utils
from utils.progress_bar import tqdm


DESCRIPTION = "Load symbol table details from analysis output"


def main(START_FOLDER):
  """
  The SymbolRewriter binary (which really needs a better name at this point...)
  emits a partial symbol table that can be used to fine tune module boundaries.

  :return: The loaded symbol tables, a pair of dicts.
  """
  definitions = dict()
  definition_files = list(filter(
        lambda s: s.endswith('-definitions.txt'),
        utils.walk_folder(START_FOLDER)))
  for emitted_file in tqdm(definition_files,
                           desc="Loading symbol table",
                           unit='definition file'):
    with open(emitted_file, 'r') as handle:
      for line in handle:
        # Parse the output of the directive file. A line is formatted like:
        #     main.cpp##1##1##MyClass
        try:
          file, _, _, symbol_name = line.strip().split('##')
          file = utils.strip_folder(START_FOLDER, file)

          utils.append_to_dict_element(definitions,
                                       symbol_name,
                                       file,
                                       set(),
                                       set.add)
        except IndexError:
          utils.logging.essential("Invalid directive in file:\n\t%s" % line,
                                  file=sys.stderr)
          continue

  for symbol, files in filter(lambda e: len(e[1]) > 1,
                              definitions):
    utils.logging.normal("WARNING: Symbol '%s' is defined by multiple files: "
                         "%s" % (symbol, ', '.join(sorted(files))),
                         file=sys.stderr)

  forward_declarations = dict()
  fwddecl_files = list(filter(
    lambda s: s.endswith('-forwarddeclarations.txt'),
    utils.walk_folder(START_FOLDER)))
  for emitted_file in tqdm(fwddecl_files,
                           desc="Loading symbol table",
                           unit='declaration file'):
    with open(emitted_file, 'r') as handle:
      for line in handle:
        # Parse the output of the directive file. A line is formatted like:
        #     main.cpp##1##1##MyClass
        try:
          file, line, _, symbol_name = line.strip().split('##')
          file = utils.strip_folder(START_FOLDER, file)

          utils.append_to_dict_element(forward_declarations,
                                       file,
                                       (int(line), symbol_name),
                                       set(),
                                       set.add)
        except IndexError:
          utils.logging.essential("Invalid directive in file:\n\t%s" % line,
                                  file=sys.stderr)
          continue

  return definitions, forward_declarations

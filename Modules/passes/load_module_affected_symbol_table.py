import sys

import utils
from utils.progress_bar import tqdm


DESCRIPTION = "Load symbol table details from analysis output"


def unpack_symbol_line(l):
  """
  Unpacks data from a single line corresponding to one symbol emitted in the
  symbol table.

  :return: A tuple of tuples.
  """
  # Parse the output of the directive file. A line is formatted like:
  #     main.cpp##1:2##1:5##MyClass
  file, begin_loc, end_loc, name = l.strip().split('##')
  begin_loc_int = list(map(int, begin_loc.split(':')))
  end_loc_int = list(map(int, end_loc.split(':')))
  begin_row, begin_col = begin_loc_int[0], begin_loc_int[1]
  end_row, end_col = end_loc_int[0], end_loc_int[1]

  return file, (begin_row, begin_col), (end_row, end_col), name


def main(START_FOLDER):
  """
  The SymbolAnalyser binary emits a partial symbol table that can be used to
  fine tune module boundaries.

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
        try:
          file, begin_loc, end_loc, symbol_name = unpack_symbol_line(line)
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
        try:
          file, (begin_line, begin_col), end_loc, symbol_name = \
            unpack_symbol_line(line)
          file = utils.strip_folder(START_FOLDER, file)

          utils.append_to_dict_element(forward_declarations,
                                       file,
                                       (begin_line, symbol_name),
                                       set(),
                                       set.add)
        except IndexError:
          utils.logging.essential("Invalid directive in file:\n\t%s" % line,
                                  file=sys.stderr)
          continue

  return definitions, forward_declarations

import sys

import utils
from utils.progress_bar import tqdm


DESCRIPTION = "Rename conflicting symbols"


def main(START_FOLDER):
  # The symbol rewriter binary creates outputs for files specifying in which
  # file at what position a rename must be made so concatenated implementation
  # files will work without name collisions that previously were not a problem
  # when implementation files were different TUs.
  symbol_rename_files = list(filter(lambda s: s.endswith("-badsymbols.txt"),
                                    utils.walk_folder(START_FOLDER)))
  for directive_file in tqdm(symbol_rename_files,
                             desc="Renaming problematic symbols",
                             unit='file'):
    with open(directive_file, 'r') as directive_handle:
      for line in reversed(list(directive_handle)):
        # Parse the output of the directive file. A line is formatted like:
        #     main.cpp##1:1##Foo##main_Foo
        # The directives must be parsed in reverse order, because it could be
        # that the same line is to be modified multiple times, and a
        # modification earlier than the next in the line will make the column
        # for the given line invalid.
        try:
          parts = line.strip().split('##')
          filename = parts[0]
          row, col = parts[1].split(':')
          from_str = parts[2]
          to_str = parts[3]

          success = utils.replace_at_position(filename,
                                              int(row), int(col),
                                              from_str, to_str)
          if not success:
            tqdm.write("Replacement failed for directive: %s" % line,
                       file=sys.stderr)
        except IndexError:
          tqdm.write("Invalid directive in file:\n\t%s" % line,
                     file=sys.stderr)
          continue

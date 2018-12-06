import multiprocessing
import os
import sys

import utils


STAGE_NAME = "Execute SymbolRewriter"


def main(SYMBOL_REWRITER_BINARY, COMPILE_COMMAND_JSON, START_FOLDER):
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

  # The SYMBOL_REWRITER_BINARY emits some definition text files which are
  # parsed and used by later steps. However, for certain translation units,
  # these files might be empty, so it would be an extra step to read these.
  for emitted_file in filter(
        lambda s: s.endswith(('-symbols.txt',
                              '-implements.txt')),
        utils.walk_folder(START_FOLDER)):
    with open(emitted_file, 'r') as handle:
      if os.fstat(handle.fileno()).st_size == 0:
        os.unlink(emitted_file)
        continue

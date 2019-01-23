import datetime
import multiprocessing
import os
import subprocess
import sys

import utils


DESCRIPTION = "Run SymbolRewriter to analyse the project for problematic " \
              "symbols"


def main(SYMBOL_REWRITER_BINARY,
         ALWAYS_DO_ANALYSIS,
         COMPILE_COMMAND_JSON,
         START_FOLDER):
  """
  In the end, after some heuristics, C++ files will be concatenated after one
  another into a "new TU" (of the module) which makes this new TU not compile
  as it is, because, for example, there are types in the anonymous namespace
  that conflict with a later file fragment.
  """
  analysis_success_path = os.path.join(START_FOLDER, 'symbol-analysis-done')
  if ALWAYS_DO_ANALYSIS and os.path.isfile(analysis_success_path):
    os.unlink(analysis_success_path)
  if os.path.isfile(analysis_success_path):
    utils.logging.normal("Not doing analysis of symbols as a previous "
                         "analysis has already been done. Specify "
                         "'--force-reanalysis' to ignore this.")
    return

  # By default don't show the progress messages.
  LOGGING = utils.logging.get_configuration()
  log_args = {'stdout': subprocess.PIPE,
              'stderr': subprocess.PIPE}
  if not LOGGING.get('compiler', True):
    # By default, show the compiler warnings/errors, only hide them if the
    # user requested it.
    log_args = {'stderr': subprocess.DEVNULL}
  if LOGGING.get('verbose', False):
    log_args['stdout'] = None

  success, _, output = utils.call_process(
    SYMBOL_REWRITER_BINARY,
    [os.path.dirname(COMPILE_COMMAND_JSON),
     str(multiprocessing.cpu_count())],
    cwd=START_FOLDER,
    **log_args)
  if not success:
    utils.logging.essential("Error: Analysing of project failed.",
                            file=sys.stderr)
    sys.exit(1)

  with open(analysis_success_path, 'w') as f:
    now = datetime.datetime.now()
    f.write("Successful analysis done at: ")
    f.write(now.isoformat())
    f.write(" .\n")

  # The SYMBOL_REWRITER_BINARY emits some definition text files which are
  # parsed and used by later steps. However, for certain translation units,
  # these files might be empty. These can be eliminated to not run extra steps
  # later.
  for emitted_file in filter(
        lambda s: s.endswith(('-badsymbols.txt',
                              '-implements.txt',
                              '-forwarddeclarations.txt',
                              '-definitions.txt')),
        utils.walk_folder(START_FOLDER)):
    with open(emitted_file, 'r') as handle:
      if os.fstat(handle.fileno()).st_size == 0:
        os.unlink(emitted_file)
        continue

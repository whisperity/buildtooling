import codecs
import json
import os
import shlex

from utils import logging
from utils.progress_bar import tqdm


DESCRIPTION = "Parse include path directives (-I) from compilation database"


def _replace_all(str, *needles):
  for needle in needles:
    str = str.replace(needle, '')
  return str


def main(COMPILE_COMMANDS_JSON):
  """
  Load the compiler include path options (-I... flags) from the compilation
  database to be used for finding includes in the Python-based include
  analyser.

  :returns: The list of includes for the project, in order they were seen. This
  list is distinct.
  """
  include_search_paths = list()
  include_search_set = set()

  def _add_include_path(path):
    path = os.path.relpath(path)
    if path in include_search_set:
      return

    logging.verbose("Will also use '%s' as include search directory..." % path)
    include_search_set.add(path)
    include_search_paths.append(path)

  logging.normal("Loading compilation database '%s'..."
                 % COMPILE_COMMANDS_JSON)

  with codecs.open(COMPILE_COMMANDS_JSON, 'r',
                   encoding='utf-8', errors='replace') as cdb_fd:
    cdb = json.load(cdb_fd)

  # Try to fetch include paths from build commands. CodeChecker has a much
  # better implementation at this, so it might worth to try using that in the
  # future...
  for i, entry in tqdm(enumerate(cdb),
                       desc="Searching for include directories",
                       total=len(cdb),
                       unit='build'):
    args = entry.get('arguments', list())
    if not args:
      args = shlex.split(entry['command'])
    if not args:
      logging.essential("Invalid entry at ID #%d in the compilation database, "
                        "no command-line found?" % i)
      continue

    for i, arg in enumerate(args):
      if arg.startswith(('-I', '-iquote', '-isystem', '-idirafter')):
        arg = _replace_all(arg, '-I', '-iquote', '-isystem', '-idirafter')
        if not arg:
          # If the argument became empty, it is a multi-word argument, and the
          # real include path value is the next argument.
          arg = args[i + 1]

        _add_include_path(arg)

  logging.verbose("Additional include paths:")
  for ip in include_search_paths:
      logging.verbose("    - %s" % (ip))

  return include_search_paths

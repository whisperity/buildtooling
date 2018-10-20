import os
import re
import sys
from collections import Counter

from utils import strip_folder, walk_folder
from utils.progress_bar import tqdm
from . import include


MODULE_MACRO = re.compile(r'FULL_NAME_(?P<name>[\w_\-\d]+)?;[\s]*$')


def get_module_mapping(srcdir):
  """
  Reads up the current working directory and create a mapping of which
  source file (as a module fragment) is mapped into which module.
  """
  ret = {}

  # Read the files and create the mapping.
  for file in tqdm(walk_folder(srcdir),
                   desc="Searching for module files...",
                   total=len(list(walk_folder(srcdir))),
                   unit='file'):
    if not file.endswith('cppm'):
      continue

    with open(file, 'r') as f:
      # Find the module's "inner name" from the 'export module' statement.
      module_name = None
      for line in f.readlines():
        if not line.startswith('export module'):
          continue

        line = line.replace('export module ', '')
        match = MODULE_MACRO.match(line)
        if not match:
          tqdm.write("Error! Cannot read input file '%s' because "
                     "'export module' line is badly formatted.\n%s"
                     % (file, line),
                     file=sys.stderr)
          break
        module_name = match.group('name')
        break

      if not module_name:
        # Skip parsing the file if it was bogus.
        continue

      ret[module_name] = {'file': file,
                          'fragments': [],
                          'imported-modules': set()
                          }
      f.seek(0)
      for line in f.readlines():
        included = include.directive_to_filename(line)
        if not included:
          continue

        included_local = os.path.join(os.path.dirname(file), included)

        if not os.path.isfile(included_local):
          tqdm.write("Error: '%s' includes '%s' but that file could not be "
                     "found." % (file, included_local),
                     file=sys.stderr)
          continue

        ret[module_name]['fragments'].append(
          strip_folder(srcdir, included_local))

  # Check for files that are (perhaps accidentally) included in multiple module
  # files.
  counts = Counter(get_all_files(ret))
  for key, value in ret.items():
    ret[key]['fragments'] = list(filter(lambda x: counts[x] == 1,
                                        value['fragments']))

  duplicated = list(dict(filter(lambda it: it[1] != 1,
                                counts.items()))
                    .keys())

  return ret, duplicated


def get_all_files(modulemapping):
  """
  Retrieve a generator for all the "fragment files" included into the modules
  in the given modulemapping.
  """
  for v in modulemapping.values():
    for f in v['fragments']:
      yield f
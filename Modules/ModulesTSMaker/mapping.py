import codecs
import os
import re
import sys
from collections import Counter

try:
  import toposort
except ImportError as e:
  print("Error! A dependency of this tool could not be satisfied. Please "
        "install the following Python package via 'pip' either to the "
        "system, or preferably create a virtualenv.")
  print(str(e))
  raise

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


def write_topological_order(module_file,
                            fragments,
                            header_regex,
                            intramodule_dependencies):
  """
  Calculate and write topological ordering of headers based on the built
  intra-dependency map. This ensures that header file "fragments" included into
  the same module will follow each other in an order that types introduced
  in the local module and used there is satisfied.
  """
  try:
    header_topological = [list(files) for files in
                          list(toposort.toposort(intramodule_dependencies))]
  except toposort.CircularDependencyError:
    print("Error! Circular dependency found in header files used in module "
          "%s. Module file cannot be rewritten!" % module,
          file=sys.stderr)
    return False

  header_fragments = list(
    filter(header_regex.search, fragments))
  with codecs.open(module_file, 'r+',
                   encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

    # Find the "part" of the module file where the header fragments are
    # included.
    first_header_include, last_header_include = None, None
    for num, l in enumerate(lines):
      if os.path.basename(header_fragments[0]) in l:
        first_header_include = num
      elif os.path.basename(header_fragments[-1]) in l:
        last_header_include = num
        break

    if not first_header_include or not last_header_include:
      print("Error! Module file '%s' included %s, %s at first read,"
            "but the directive cannot be found..."
            % (module_file, header_fragments[0], header_fragments[-1]),
            file=sys.stderr)
      return False

    # Rewrite this part to contain the topological order of headers.
    new_includes = []
    for group in header_topological:
      group.sort()
      for file in group:
        # Modules usually include files relative to the module file's own
        # location, but the script knows them relative to the working directory
        # at the start...
        file = file.replace(os.path.dirname(module_file), '').lstrip('/')
        new_includes.append("#include \"%s\"\n" % file)
      new_includes.append('\n')

    lines = lines[:first_header_include] + \
            new_includes[:-1] + \
            lines[last_header_include + 1:]

    f.seek(0)
    f.writelines(lines)
    f.truncate(f.tell())

  return True
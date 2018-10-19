#!/usr/bin/env python3

import codecs
import os
import re
import sys
from collections import Counter
from itertools import filterfalse, tee

try:
  import toposort
except ImportError as e:
  print("Error! A dependency of this tool could not be satisfied. Please "
        "install the following Python package via 'pip' either to the "
        "system, or preferably create a virtualenv.")
  print(str(e))
  sys.exit(1)

try:
  from tqdm import tqdm
except ImportError:
  class tqdm():
    """
    tqdm progress bar wrapper if the 'tqdm' package is not installed.
    """

    def __init__(self, iterable, *i, **kwargs):
      self.iterable = iterable
      self.total = kwargs.get('total', None)

    def __enter__(self):
      return self

    def __exit__(self, *exc):
      return False

    def __del__(self):
      pass

    def __iter__(self):
      for e in self.iterable:
        yield e

    def __len__(self):
      return self.total if self.iterable is None else \
        (self.iterable.shape[0] if hasattr(self.iterable, "shape")
         else len(self.iterable) if hasattr(self.iterable, "__len__")
        else getattr(self, "total", None))

    @staticmethod
    def write(*args, **kwargs):
      return print(*args, **kwargs)


  print("Python library 'tqdm' not found, no progress will be printed.",
        file=sys.stderr)
  #tqdm = lambda *i, **kwargs: i[0]  # pylint:disable=invalid-name


def concatenate_files(header, source):
  """
  Read the specified header and source file and concatenate them in
  "header, source" order.
  """
  content = ""

  if (header):
    content = """
// +*************************************************************************+
//   Begin header file '%s'
// +*************************************************************************+

""" % header

    with codecs.open(header, 'r', encoding='utf-8', errors='replace') as hdr:
      content += hdr.read()

    content += """
// +*************************************************************************+
//   End header file '%s'
// +*************************************************************************+
""" % header

  if (source):
    content += """
// +*************************************************************************+
//   Begin implementation file '%s'
// +*************************************************************************+

""" % source

    with codecs.open(source, 'r', encoding='utf-8', errors='replace') as src:
      content += src.read()

    content += """
// +*************************************************************************+
//   End implementation file '%s'
// +*************************************************************************+

""" % source

  return content


if not os.path.isfile("CMakeLists.txt"):
  print("Error: this script should be run from a source folder.",
        file=sys.stderr)
  sys.exit(2)


def partition(pred, iterable):
  """Partition an iterable to entries that pass or not pass a predicate."""
  it1, it2 = tee(iterable)
  return filterfalse(pred, it1), filter(pred, it2)


def strip_folder(folder, path):
  return os.path.abspath(path) \
         .replace(os.path.abspath(folder), '') \
         .lstrip('/')


def walk_folder(folder):
  for dirp, _, files in os.walk(folder):
    for file in files:
      yield strip_folder(folder, os.path.join(dirp, file))


def include_line_to_filename(line):
  if not line.startswith('#include'):
    return None

  return line \
    .replace('#include ', '') \
    .strip() \
    .lstrip(r'"<') \
    .rstrip(r'">')


def get_module_map(folder):
  """
  Reads up the current working directory and create a mapping of which
  source file (as a module fragment) is mapped into which module.
  """

  ret = {}
  module_macro = re.compile(r'FULL_NAME_(?P<name>[\w_\-\d]+)?;[\s]*$')

  # Read the files and create the mapping.
  for file in tqdm(walk_folder(folder),
                   desc="Searching for module files...",
                   total=len(list(walk_folder(folder))),
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
        match = re.match(module_macro, line)
        if not match:
          tqdm.write("Error! Cannot read input file '%s' because "
                     "'export module' line is badly formatted.\n%s"
                     % (file, line), file=sys.stderr)
          break
        module_name = match.group('name')
        break

      if not module_name:
        # Skip parsing the file if it was bogus.
        continue

      ret[module_name] = []
      f.seek(0)
      for line in f.readlines():
        included = include_line_to_filename(line)
        if not included:
          continue

        included_local = os.path.join(os.path.dirname(file), included)

        if not os.path.isfile(included_local):
          tqdm.write("Error: '%s' includes '%s' but that file could not be "
                     "found." % (file, included_local),
                     file=sys.stderr)
          continue

        ret[module_name].append(strip_folder(folder, included_local))

  return ret


def eliminate_duplicate_values(d):
  """
  Eliminates the duplicate values in a dict's value side.
  :returns: The eliminated dict, and the list of duplicate values.
  """
  counts = Counter(sum(d.values(), []))
  for key, value in d.items():
    d[key] = list(filter(lambda x: counts[x] == 1, value))

  return d, \
    list(
      dict(
        filter(lambda it: it[1] != 1,
               counts.items()))
      .keys())


MODULEMAP = get_module_map(os.getcwd())
MODULEMAP, duplicates = eliminate_duplicate_values(MODULEMAP)

if duplicates:
  print("Error: Some files are included into multiple modules. These files "
        "had been removed from the mapping!", file=sys.stderr)
  print('\n'.join(duplicates), file=sys.stderr)


def handle_source_text(modulemap, self_dependency_map, file, text):
  """
  Handles mapping the #include statements to modules in a concatenated source
  text.
  """

  # Get the "first" module from the module map read earlier which contains
  # the included file as its own include (so the included file's code is
  # in the said module).
  # First is good enough as the module map was uniqued out earlier.
  def __get_module(include):
    return next(
      filter(
        lambda item: include in item[1],
        modulemap.items()),
      (None, None))[0]

  # Rearrange the include statements so all of them are on the top, and for
  # easier rewriting to "import", in alphabetical order.

  include_lines, other_lines = partition(
    lambda line: not line.startswith("#include"),
    text.splitlines(True))
  include_lines = list(sorted(include_lines))

  self_module = __get_module(file)

  if not include_lines:
    # If the file contains no "#include" statements, no need to do anything.
    return

  found_used_modules = set()
  lines_to_keep = []
  for line in tqdm(include_lines,
                   unit='directives',
                   desc=os.path.basename(file),
                   position=0,
                   leave=False):
    included = include_line_to_filename(line)
    if not included:
      continue

    module = __get_module(included)
    if not module:
      # If no module is found for the include, it might have been an include
      # from the local folder. Let's try that way first...
      included = os.path.join(os.path.dirname(file), included)
      module = __get_module(included)
    if not module:
      tqdm.write("%s: Included '%s' not found in module map"
                 % (file, included),
                 file=sys.stderr)
      lines_to_keep.append(line.strip())
      continue

    if module == self_module and self_module is not None:
      # Files can transitively and with the employment of header guards,
      # recursively include each other, which is not a problem in normal C++,
      # but for imports this must be evaded, as the files are put into a module
      # wrapper, which should not include itself.
      # However, for this module "wrapper" file to work, the includes of the
      # module "fragments" (which are rewritten by this script) must be in
      # a good order.
      if self_module not in self_dependency_map:
        self_dependency_map[self_module] = {}
      if file not in self_dependency_map[self_module]:
        self_dependency_map[self_module][file] = set()
      self_dependency_map[self_module][file].add(included)
    else:
      found_used_modules.add(module)

  new_includes = "/* Automatically generated include list. */\n" + \
                 '\n'.join(lines_to_keep) + \
                 "\n\n" + \
                 '\n'.join(["import MODULE_NAME_" + mod + ';'
                            for mod in found_used_modules])

  with open(os.devnull, 'w') as f:
    f.write(new_includes)
    f.write("\n\n")
    f.write('\n'.join(other_lines))


SELF_DEPENDENCY_MAP = {}

# Check for headers that may or may not have an implementation CPP to them.
for file in tqdm(walk_folder(os.getcwd()),
                 unit='files',
                 desc="Iface-Impl pairs",
                 total=len(list(walk_folder(os.getcwd()))),
                 position=1):
  if not file.endswith('.hpp'):
    continue

  cpp_path = file.replace('.hpp', '.cpp')
  if not os.path.isfile(cpp_path):
    # If the header does not have an implementation pair, do only the header.
    cpp_path = None

  handle_source_text(MODULEMAP, SELF_DEPENDENCY_MAP,
                     file, concatenate_files(file, cpp_path))

# Check for source files that do not have a header named like them.
for file in tqdm(walk_folder(os.getcwd()),
                 unit='files',
                 desc="Solo impl. files",
                 total=len(list(walk_folder(os.getcwd()))),
                 position=1):
  if not file.endswith('.cpp'):
    continue

  hpp_path = file.replace('.cpp', '.hpp')
  if os.path.isfile(hpp_path):
    # If the implementation file had a header pair with it, it is already
    # handled.
    continue

  handle_source_text(MODULEMAP, SELF_DEPENDENCY_MAP,
                     file, concatenate_files(None, file))

import json
#print(json.dumps(SELF_DEPENDENCY_MAP, indent=2, sort_keys=True))

for module in SELF_DEPENDENCY_MAP.keys():
  try:
    topo = toposort.toposort(SELF_DEPENDENCY_MAP[module])
    topo = list(topo)
    print("MODULE %s DEPENDENCIES" % module)
    topo = [list(x) for x in list(topo)]  # Convert sets to lists...
    print(json.dumps(topo, indent=2, sort_keys=False))
  except toposort.CircularDependencyError:
    # print("Circular dependency in module '%s'." % module, file=sys.stderr)
    # print("Ignoring for now...", file=sys.stderr)
    pass

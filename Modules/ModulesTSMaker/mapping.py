import codecs
import itertools
import os
import re
import sys
from collections import Counter

try:
  import networkx as nx
except ImportError as e:
  print("Error! A dependency of this tool could not be satisfied. Please "
        "install the following Python package via 'pip' either to the "
        "system, or preferably create a virtualenv.")
  raise

from utils import strip_folder, walk_folder
from utils.progress_bar import tqdm
from . import include

MODULE_MACRO = re.compile(r'FULL_NAME_(?P<name>[\w_\-\d]+)?;[\s]*$')


class ModuleMapping():
  """
  A module mapping contains the list of fragment files, inclusion directives
  that are known to be mapped into a particular module file.
  """
  def __init__(self):
    self._map = dict()

  def __contains__(self, module):
    return module in self._map.keys()

  def __len__(self):
    return len(self._map.keys())

  def __iter__(self):
    return iter(self._map.keys())

  def add_module(self, name, module_file):
    if name not in self:
      self._map[name] = {'file': module_file,
                         'fragments': [],
                         'imported-modules': set()
                         }

  def add_fragment(self, module, fragment_file):
    if module not in self:
      raise KeyError("Cannot add a fragment to a module that has not been "
                     "added.")

    self._map[module]['fragments'].append(fragment_file)

  def get_filename(self, module):
    if module not in self:
      raise KeyError("Module '%s' not found in the module mapping." % module)
    return self._map[module]['file']

  def get_fragment_list(self, module):
    if module not in self:
      raise KeyError("Cannot get fragments for a module that has not been "
                     "added.")
    return self._map[module]['fragments']

  def get_all_fragments(self):
    """
    Retrieve a generator for all the "fragment files" included into the modules
    in the mapping.
    """
    for v in self._map.values():
      for f in v['fragments']:
        yield f

  def get_modules_for_file(self, file):
    """
    Returns the list of modules where the given :param file: was mapped into.
    """
    return map(lambda i: i[0],  # Return the key, the module's name.
               filter(
                 lambda i: file in i[1]['fragments'],
                 self._map.items()))

  def add_module_import(self, module, dependency):
    if module not in self:
      raise KeyError("Module '%s' not found in the module mapping." % module)
    if dependency not in self:
      raise KeyError("Module '%s' not found in the module mapping."
                     % dependency)

    self._map[module]['imported-modules'].add(dependency)

  def get_dependencies_of_module(self, module):
    if module not in self:
      raise KeyError("Cannot get fragments for a module that has not been "
                     "added.")
    return self._map[module]['imported-modules']


class DependencyMap():
  """
  A dependency map contains information of dependencies of (module, file)
  pairs.
  """
  def __init__(self, module_mapping):
    self._module_mapping = module_mapping
    self._map = dict()

  def __contains__(self, item):
    """
    Returns if a dependency is known for the given file, or module.
    """
    return item in self._map.keys() or any([item in module
                                            for module in self._map])

  def add_dependency(self, dependee, dependency):
    """
    Add the dependency that :param dependee: depends on :param dependency:.
    """
    dependee_modules = self._module_mapping.get_modules_for_file(dependee)
    dependency_modules = self._module_mapping.get_modules_for_file(dependency)

    for mod in dependee_modules:
      if mod not in self._map:
        self._map[mod] = dict()
      if dependee not in self._map[mod]:
        self._map[mod][dependee] = dict()

      for dep in dependency_modules:
        if dep not in self._map[mod][dependee]:
          self._map[mod][dependee][dep] = []
        if dependency not in self._map[mod][dependee][dep]:
          self._map[mod][dependee][dep].append(dependency)

  def get_files_creating_dependency_between(self, from_module, to_module):
    """
    Retrieve the list of files that are the reason that :param from_module:
    depends on :param to_module:.

    :return: A dictionary object containing a filename => set of filenames
    mapping.
    """
    ret = dict()
    for from_file in self._map.get(from_module, []):
      ret[from_file] = set()
      for to_file in self._map[from_module][from_file].get(to_module, []):
        ret[from_file].add(to_file)

      if len(ret[from_file]) == 0:
        del ret[from_file]
    return ret

  def get_intramodule_dependencies(self, module):
    """
    Get the list of dependencies of files in :param module: which are also in
    :param module:.

    :return: A dictionary object containing a filename => set of filenames
    mapping.
    """
    return self.get_files_creating_dependency_between(module, module)


def get_module_mapping(srcdir):
  """
  Reads up the current working directory and create a mapping of which
  source file (as a module fragment) is mapped into which module.
  """
  mapping = ModuleMapping()

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

      mapping.add_module(module_name, file)
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

        mapping.add_fragment(module_name,
                             strip_folder(srcdir, included_local))

  # Check for files that are (perhaps accidentally) included in multiple module
  # files.
  counts = Counter(mapping.get_all_fragments())
  for module in mapping:
    fragments = mapping.get_fragment_list(module)
    for file in list(filter(lambda x: counts[x] != 1, fragments)):
      fragments.remove(file)

  duplicated = list(dict(filter(lambda it: it[1] != 1,
                                counts.items()))
                    .keys())

  return mapping, duplicated


def get_modules_circular_dependency(module_map, dependency_map):
  """
  """
  dependencies = dict(
    map(lambda m: (m, module_map.get_dependencies_of_module(m)),
        module_map))
  graph = nx.DiGraph(dependencies)
  if nx.is_directed_acyclic_graph(graph):
    return True

  cycles = list(nx.simple_cycles(graph))
  smallest_cycles_length = min([len(c) for c in cycles])
  for cycle in filter(lambda x: len(x) == smallest_cycles_length, cycles):
    print("Circular dependency between modules found on the following path:")
    print("    %s" % ' -> '.join(cycle + [cycle[0]]))

    # Make sure it is "actually" a cycle.
    cycle.append(cycle[0])

    for a, b in itertools.zip_longest(cycle[:-1], cycle[1:]):
      print(a, b)
      files = dependency_map.get_files_creating_dependency_between(a, b)
      for k, v in files.items():
        files[k] = list(v)
      import json
      print(json.dumps(files, indent=2))

    break

  return False


def write_topological_order(module_file,
                            fragments,
                            regex,
                            intramodule_dependencies):
  """
  Calculate and write topological ordering of files based on the built
  intra-dependency map. This ensures that file "fragments" included into
  the same module will follow each other in an order that depend on each other
  are satisfied without the use of header guards.
  """
  try:
    graph = nx.DiGraph(intramodule_dependencies)
    topological = list(nx.topological_sort(graph))
  except nx.NetworkXUnfeasible:
    print("Error! Circular dependency found in header files used in module "
          "%s. Module file cannot be rewritten!" % module_file,
          file=sys.stderr)
    return False

  filtered_fragments = list(filter(regex.search, fragments))
  with codecs.open(module_file, 'r+',
                   encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

    # Find the "part" of the module file where the header fragments are
    # included.
    first_header_include, last_header_include = None, None
    for num, l in enumerate(lines):
      if os.path.basename(filtered_fragments[0]) in l:
        first_header_include = num
      elif os.path.basename(filtered_fragments[-1]) in l:
        last_header_include = num
        break

    if not first_header_include or not last_header_include:
      print("Error! Module file '%s' included %s, %s at first read,"
            "but the directive cannot be found..."
            % (module_file, filtered_fragments[0], filtered_fragments[-1]),
            file=sys.stderr)
      return False

    # Rewrite this part to contain the topological order of headers.
    new_includes = []
    for file in topological:
      # Modules usually include files relative to the module file's own
      # location, but the script knows them relative to the working directory
      # at the start...
      file = file.replace(os.path.dirname(module_file), '').lstrip('/')
      new_includes.append("#include \"%s\"\n" % file)

    lines = lines[:first_header_include] + \
            new_includes[:-1] + \
            lines[last_header_include + 1:]

    f.seek(0)
    f.writelines(lines)
    f.truncate(f.tell())

  return True

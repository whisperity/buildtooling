import codecs
import os
import re
import sys
from collections import Counter
from hashlib import md5
from operator import itemgetter

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
MEMORY_ONLY_MODULE_BACKING_FILENAME = os.devnull


def substitute_module_macro(name):
  return "#define MODULE_EXPORT\n" \
         "export module FULL_NAME_" + name + ";\n"


def substitute_module_import(name):
  return "import MODULE_NAME_" + name + ";\n"


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

  def __delitem__(self, module):
    if module not in self:
      return
    del self._map[module]

  def add_module(self, module, backing_file):
    if module in self:
      raise KeyError("Cannot add a module twice.")

    self._map[module] = {'file': backing_file,
                         'fragments': [],
                         'imported-modules': set(),
                         'tainted': True
                         }

  def set_backing_file(self, module, backing_file):
    if module not in self:
      raise KeyError("Cannot set the backing file of a module that has not "
                     "been added.")
    self._map[module]['file'] = backing_file
    self._map[module]['tainted'] = True

  def set_not_tainted(self, module=None):
    """
    Sets the given :param module_name: or all modules to NOT tainted.
    """
    if module:
      if module not in self:
        raise KeyError("Cannot untaint a module that has not been added.")
      self._map[module]['tainted'] = False
    else:
      for key in self:
        self._map[key]['tainted'] = False

  def add_fragment(self, module, fragment_file):
    if module not in self:
      raise KeyError("Cannot add a fragment to a module that has not been "
                     "added.")
    self._map[module]['fragments'].append(fragment_file)
    self._map[module]['tainted'] = True

  def remove_fragment(self, fragment_file):
    """
    Unmaps the given :param fragment_file: from all modules it is mapped to.
    """
    modules_gone_empty = list()
    for module in self.filter_modules_for_fragments([fragment_file]):
      self._map[module]['fragments'].remove(fragment_file)
      self._map[module]['tainted'] = True

      if not self._map[module]['fragments']:
        modules_gone_empty.append(module)

    for module in modules_gone_empty:
      # TODO: Allow client code to obtain this deletion information so
      # physical files can be cleaned up.
      # del self._map[module]
      pass

  def get_filename(self, module):
    if module not in self:
      raise KeyError("Module '%s' not found in the module mapping." % module)
    return self._map[module]['file']

  def is_tainted(self, module):
    if module not in self:
      raise KeyError("Module '%s' not found in the module mapping." % module)
    return self._map[module]['tainted']

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

  def get_modules_for_fragment(self, fragment_file):
    """
    Returns the list of modules where the given :param fragment_file: was
    mapped into.
    """
    return map(itemgetter(0),  # Return the key, the module's name.
               filter(
                 lambda i: fragment_file in i[1]['fragments'],
                 self._map.items()))

  def filter_modules_for_fragments(self, fragments):
    """
    :return: A dict which maps only the fragment files specified in
    :param fragments: to modules they belong to.
    """
    ret = dict()

    for fragment in fragments:
      for module in self.get_modules_for_fragment(fragment):
        file_list_for_module = ret.get(module, list())
        if len(file_list_for_module) == 0:
          # A new list was created, append it to the dict.
          ret[module] = file_list_for_module

        file_list_for_module.append(fragment)

    return ret

  def add_module_import(self, module, dependency):
    if module not in self:
      raise KeyError("Module '%s' not found in the module mapping." % module)
    if dependency not in self:
      raise KeyError("Module '%s' not found in the module mapping."
                     % dependency)

    self._map[module]['imported-modules'].add(dependency)

  def get_dependencies_of_module(self, module):
    if module not in self:
      raise KeyError("Cannot get dependencies for a module that has not been "
                     "added.")
    return self._map[module]['imported-modules']

  def clear_module_imports(self, module):
    if module not in self:
      raise KeyError("Cannot clear dependencies for a module that has not "
                     "been added.")
    self._map[module]['imported-modules'] = set()


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

  def get_module_map(self):
    """
    :return: The :type ModuleMapping: that was attached to the current
    :type DependencyMap:.
    """
    return self._module_mapping

  def add_dependency(self, dependee, dependency, kind="uses"):
    """
    Add the dependency that :param dependee: depends on :param dependency:.

    :param kind: should be `uses` or `implements`.
    """
    if kind not in ['uses', 'implements']:
      raise ValueError("'kind' should be either 'uses' or 'implements'.")

    dependee_modules = list(
      self._module_mapping.get_modules_for_fragment(dependee))
    dependency_modules = list(
      self._module_mapping.get_modules_for_fragment(dependency))

    if not dependee_modules:
      raise ValueError("Cannot add dependency of '%s' because it is not "
                       "assigned to any module." % dependee)
    if not dependency_modules:
      raise ValueError("Cannot add dependency for '%s' because it is not "
                       "assigned to any module." % dependency)

    for mod in dependee_modules:
      if mod not in self._map:
        self._map[mod] = dict()
      if dependee not in self._map[mod]:
        self._map[mod][dependee] = dict()

      for dep in dependency_modules:
        if dep not in self._map[mod][dependee]:
          self._map[mod][dependee][dep] = {'uses': [],
                                           'implements': []}
        if dependency not in self._map[mod][dependee][dep][kind]:
          self._map[mod][dependee][dep][kind].append(dependency)

  def remove_file(self, filename):
    """
    Removes the given :param filename: from the dependency map. Every
    depedency incident to the file is removed.
    """
    modules_to_remove = list()

    for module in self._map:
      if filename in self._map[module]:
        # Found a module which contains 'filename', and dependency information
        # of it. File is deleted, so remove the entire inner dict.
        del self._map[module][filename]
        if not self._map[module]:
          # The module has emptied out.
          modules_to_remove.append(module)

      files_to_remove_from_module = list()
      for file_in_module in self._map[module]:
        inner_modules_to_remove = list()
        for dep_module, dep_filedict in \
              self._map[module][file_in_module].items():
          for kind in dep_filedict:
            if filename in dep_filedict[kind]:
              # Remove the file from every file's dependency list, if found.
              dep_filedict[kind].remove(filename)

          if all(not l for l in dep_filedict.values()):
            # The dependency list of module 'dep_module' for
            # 'file_in_module' has emptied out, remove this entry.
            inner_modules_to_remove.append(dep_module)

        for remove_module in inner_modules_to_remove:
          # Clear module-level dependency if now in fact the file does not
          # depend on said module anymore.
          del self._map[module][file_in_module][remove_module]

        if not self._map[module][file_in_module]:
          files_to_remove_from_module.append(file_in_module)

      for remove_from_module in files_to_remove_from_module:
        del self._map[module][remove_from_module]

    for remove_module in modules_to_remove:
      del self._map[remove_module]

  def get_dependencies(self, filename):
    """
    :return: A collection of files :param filename: depends on, across every
    module.
    """
    ret = {'uses': set(), 'implements': set()}
    modules = self._module_mapping.get_modules_for_fragment(filename)

    for mod in modules:
      if mod not in self._map:
        continue
      if filename not in self._map[mod]:
        continue

      for dependency_module in self._map[mod][filename]:
        ret['uses'].update(
          set(self._map[mod][filename][dependency_module]['uses']))
        ret['implements'].update(
          set(self._map[mod][filename][dependency_module]['implements']))

    return ret

  def get_dependees(self, filename):
    """
    :return: A collection of files depending on :param filename:, across every
    module.
    """
    ret = set()

    for mod in self._map:
      for dependee_file in self._map[mod]:
        for dependee_module in self._map[mod][dependee_file]:
          for kind in self._map[mod][dependee_file][dependee_module]:
            if filename in \
                  self._map[mod][dependee_file][dependee_module][kind]:
              ret.add((dependee_file, kind))

    return ret

  def get_files_creating_dependency_between(self, from_module, to_module):
    """
    Retrieve the list of files that are the reason that :param from_module:
    depends on :param to_module:.

    :return: A dictionary object containing a filename => set of
    (filenames, kind) mapping.
    """
    ret = dict()
    for from_file in self._map.get(from_module, []):
      ret[from_file] = set()
      for kind, filelist in self._map[from_module][from_file]\
            .get(to_module, {}).items():
        for to_file in filelist:
          ret[from_file].add((to_file, kind))

      if len(ret[from_file]) == 0:
        del ret[from_file]
    return ret

  def get_intramodule_dependencies(self, module):
    """
    Get the list of dependencies of files in :param module: which are also in
    :param module:.

    :return: A dictionary object containing a filename => set of
    (filenames, kind) mapping.
    """
    return self.get_files_creating_dependency_between(module, module)

  def synthesize_intermodule_imports(self):
    """
    Using the dependencies stored in the current instance, synthesize a
    module-module 'import' list into the :var _module_mapping: of the instance.
    """
    for module in self._module_mapping:
      self._module_mapping.clear_module_imports(module)

    for module in self._map:
      module_dependencies = set()
      for dependency_entry in self._map[module].values():
        for module_name in dependency_entry:
          if dependency_entry[module_name]['uses']:
            # Only consider an other module to be imported if it is *used*, not
            # in the "implements" relation.
            module_dependencies.add(module_name)

      # Never consider self-dependency.
      module_dependencies.discard(module)

      for dependency in module_dependencies:
        self._module_mapping.add_module_import(module, dependency)


def get_module_mapping(srcdir):
  """
  Reads up the given :param srcdir: directory and create a mapping of which
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
  duplicated = list()
  counts = Counter(mapping.get_all_fragments())
  for module in mapping:
    fragments = mapping.get_fragment_list(module)
    for file in filter(lambda x: counts[x] != 1, fragments):
      duplicated.append(file)
      fragments.remove(file)

  mapping.set_not_tainted()
  return mapping, duplicated


def write_module_mapping(srcdir, module_map):
  """
  Write the given :param module_map: into the :param srcdir: directory as
  C++ Modules-TS module files.
  """
  old_folder = os.getcwd()
  os.chdir(srcdir)

  modules_to_delete = list()
  for module in tqdm(sorted(module_map),
                     desc="Writing new modules...",
                     total=len(module_map),
                     unit='module'):
    if not module_map.is_tainted(module):
      continue

    backing_file = module_map.get_filename(module)
    fragments = module_map.get_fragment_list(module)
    if not fragments:
      modules_to_delete.append(module)
      if backing_file != MEMORY_ONLY_MODULE_BACKING_FILENAME:
        os.unlink(backing_file)
      continue

    if backing_file == MEMORY_ONLY_MODULE_BACKING_FILENAME:
      backing_file = os.path.join(srcdir, module + '.cppm')
      module_map.set_backing_file(module, backing_file)

    with open(backing_file, 'w') as f:
      for module_dependency in sorted(
            module_map.get_dependencies_of_module(module)):
        f.write(substitute_module_import(module_dependency))

      f.writelines(['\n', substitute_module_macro(module), '\n', '\n'])

      for frag in fragments:
        frag = os.path.join(srcdir, frag)
        frag = strip_folder(os.path.dirname(backing_file), frag)

        f.write(include.filename_to_directive(frag))
        f.write('\n')

  for module_to_delete in modules_to_delete:
    del module_map[module_to_delete]

  module_map.set_not_tainted()

  os.chdir(old_folder)


def apply_file_moves(module_map, dependency_map, moved_files):
  """
  Update :param ModuleMapping: and :type DependencyMap: by applying the file
  moving to other module changes dictated by :param moved_files:.
  """
  if not moved_files:
    return

  dependencies_to_fix_up = list()
  for filename in moved_files:
    for file_depending_on_moved, dep_kind in \
          dependency_map.get_dependees(filename):
      dependencies_to_fix_up.append(
        (file_depending_on_moved, filename, dep_kind))
    for dep_kind, files in dependency_map.get_dependencies(filename).items():
      for moved_depending_on_file in files:
        dependencies_to_fix_up.append(
          (filename, moved_depending_on_file, dep_kind))

    dependency_map.remove_file(filename)

  for filename, new_module in moved_files.items():
    module_map.remove_fragment(filename)
    if new_module not in module_map:
      module_map.add_module(new_module, MEMORY_ONLY_MODULE_BACKING_FILENAME)
    module_map.add_fragment(new_module, filename)

  for dependee, dependency, kind in dependencies_to_fix_up:
    # Fix the dependency map so the file->file dependencies now point through
    # the new module names.
    dependency_map.add_dependency(dependee, dependency, kind)

  # Resynthesize the import list because file-module relations have changed.
  dependency_map.synthesize_intermodule_imports()


def get_new_module_name(module_map, moved_files, accepted_name=None):
  """
  Given a :param module_map: this function generated a name for files in
  :param moved_files:. The new module name will be something that does not
  exist in the module map already.

  If :param accepted_name: is specified and the generated name would match
  :param accepted_name:, the same value is returned, and no further
  calculations are made.
  """
  if len(moved_files) == 0:
    return None

  only_file = moved_files[0] if len(moved_files) == 1 else None
  digest = md5(','.join(moved_files).encode('utf-8')).hexdigest()

  def _get_name(sublen):
    if sublen > len(digest):
      raise IndexError("Hash length of %d exhausted" % len(digest))

    if only_file:
      file_name = os.path.splitext(os.path.basename(only_file))[0]
      return "Module_%s_%s" % (digest[:sublen], file_name)
    else:
      return "Module_%s" % digest[:sublen]

  digest_sublen = 7
  new_name = _get_name(digest_sublen)
  while new_name in module_map and new_name != accepted_name:
    digest_sublen += 1
    new_name = _get_name(digest_sublen)

  return new_name


def write_topological_order(module_file,
                            regex,
                            intramodule_dependencies):
  """
  Calculate and write topological ordering of files based on the built
  intra-dependency map. This ensures that file "fragments" included into
  the same module will follow each other in an order that depend on each other
  are satisfied without the use of header guards.

  The intramodule dependency map must contain each such files to be ordered as
  a key. If there are no dependencies, the value in the dict shall be empty, or
  empty list.
  """
  try:
    graph = nx.DiGraph(intramodule_dependencies)
    topological = nx.lexicographical_topological_sort(graph)
  except nx.NetworkXUnfeasible:
    print("Error! Circular dependency found in header files used in module "
          "%s. Module file cannot be rewritten!" % module_file,
          file=sys.stderr)
    return False

  with codecs.open(module_file, 'r+',
                   encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

    # Find the "part" of the module file where the regex-matching fragments are
    # included.
    # It's an invariant that first only such are included, and then only
    # other kinds of files!
    first_matching_include, last_matching_include = None, None
    for num, l in enumerate(lines):
      potentially_included_filename = include.directive_to_filename(l)
      if not potentially_included_filename:
        continue

      if not first_matching_include and \
            regex.search(potentially_included_filename):
        first_matching_include = num
        last_matching_include = num
        continue

      if regex.search(potentially_included_filename):
        last_matching_include = num

    if not first_matching_include or not last_matching_include:
      print("Error! No inclusion directives found in module file."
            % module_file,
            file=sys.stderr)
      return False

    # Rewrite this part to contain the topological order of files.
    new_includes = []
    for file in topological:
      # Modules usually include files relative to the module file's own
      # location, but the script knows them relative to the working directory
      # at the start...
      file = file.replace(os.path.dirname(module_file), '').lstrip('/')
      new_includes.append(include.filename_to_directive(file) + '\n')

    lines = lines[:first_matching_include] + \
            new_includes + \
            lines[last_matching_include + 1:]

    f.seek(0)
    f.writelines(lines)
    f.truncate(f.tell())

  return True


def get_dependency_map_implementation_insanity(dependency_map):
  """
  Returns whether the given :param dependency_map: (in its current state) is
  sane for the 'implements-relation' dependencies. If the map is not sane,
  returns, for each file that spans the insanity, a dict with the modules
  implementing it as keys, and a set of files as values. Otherwise, just
  returns an empty dict.

  A dependency map is implementation-sane if every file that is implemented is
  only implemented by files in at most a single module.

  :note: This operation is costly to calculate as it involves a reverse mapping
  and should not be called too many times.
  """
  file_implemented_in_module = dict()
  for file in dependency_map.get_module_map().get_all_fragments():
    file_implementees = dict()

    for dependee_tuple in dependency_map.get_dependees(file):
      dependee, kind = dependee_tuple
      if kind != 'implements':
        continue

      dependee_modules = dependency_map \
        .get_module_map() \
        .get_modules_for_fragment(dependee)
      for implementing_module in dependee_modules:
        implementees_in_module = file_implementees.get(implementing_module,
                                                       set())
        if not implementees_in_module:
          file_implementees[implementing_module] = implementees_in_module
        implementees_in_module.add(dependee)

    if file_implementees:
      file_implemented_in_module[file] = file_implementees

  # Filter the implements relations to only the files that are not sane.
  insane_implements_relations = dict(
    filter(lambda e: len(e[1]) > 1, file_implemented_in_module.items()))

  return insane_implements_relations

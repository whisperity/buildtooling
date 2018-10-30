import codecs
import itertools
import json
import os
import re
import sys
from collections import Counter
from operator import itemgetter

try:
  import matplotlib.pyplot as plt
  import networkx as nx
except ImportError as e:
  print("Error! A dependency of this tool could not be satisfied. Please "
        "install the following Python package via 'pip' either to the "
        "system, or preferably create a virtualenv.")
  raise

from utils import strip_folder, walk_folder, graph_visualisation
from utils.progress_bar import tqdm
from . import include
from . import util

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
    dependee_modules = self._module_mapping.get_modules_for_fragment(dependee)
    dependency_modules = self._module_mapping.get_modules_for_fragment(
      dependency)

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


def _create_flow_for_cycle_graph(cycle,
                                 cycle_file_graph,
                                 module_to_files_map):
  """
  Create a flow graph that has a node for each module in the :param cycle:.
  The result flow can be used to create a minimal cut for file reassignment
  into a different module.

  :param cycle_file_graph: The original dependency directed graph that links
  files to each other.
  :param module_to_files_map: A map that assigns a list of files belonging to
  a particular module.
  """
  flow = nx.DiGraph()

  for module in cycle[:-1]:  # Only iterate the path, not the full cycle.
    if module == cycle[0]:
      # Create a "start" and "end" node for the source and sink of the
      # cycle.
      dependee_node = module + ' ->'
      dependency_node = '-> ' + module

      flow.add_node(dependee_node)
      flow.add_node(dependency_node)
    else:
      # Inner elements only get one node.
      dependee_node = dependency_node = '-> ' + module + ' ->'
      flow.add_node(dependee_node)

    # filename -> (#-of-files-f-depends-upon, #-of-files-depending-on-f)
    degree_map = dict(
      map(
        lambda filename: (filename,
                          (cycle_file_graph.in_degree(filename),
                           cycle_file_graph.out_degree(filename))),
        module_to_files_map[module]))
    any_file_on_both_sides = any([d[0] > 0 and d[1] > 0 for d
                                  in degree_map.values()])

    for file_in_module in module_to_files_map[module]:
      in_degree = degree_map[file_in_module][0]
      out_degree = degree_map[file_in_module][1]

      if in_degree > 0:
        # file_in_module is a dependency of other files.
        flow.add_node('-> ' + file_in_module)

        if module == cycle[0]:
          # (If the file is in the cycle's sidemost module, write it to
          # the source.)
          flow.add_edge('-> ' + file_in_module,
                        dependency_node)

      if out_degree > 0:
        # file_in_module depends on other files.
        flow.add_node(file_in_module + ' ->')

        if module == cycle[0]:
          # (If the file is in the cycle's sidemost module, write it to
          # the sink.)
          flow.add_edge(dependee_node,
                        file_in_module + ' ->')

      if module != cycle[0]:
        if in_degree > 0 and out_degree > 0:
          # If the file is both a dependency and depends on others, link
          # the two file nodes.
          flow.add_edge('-> ' + file_in_module,
                        file_in_module + ' ->')
        else:
          # Otherwise link the file to the module on the "side" it can be
          # appropriate.
          # (Here, to ensure the flow cuts at the right position, we
          # limit the flow that can go through a file.)
          if out_degree > 0:
            flow.add_edge(dependee_node,
                          file_in_module + ' ->',
                          capacity=out_degree if any_file_on_both_sides
                          else float('inf'))
          if in_degree > 0:
            flow.add_edge('-> ' + file_in_module,
                          dependency_node,
                          capacity=in_degree if any_file_on_both_sides
                          else float('inf'))

    # If all files for the module had been added and every such file appeared
    # "on both sides" (both as a dependency and one that depends on others),
    # then the module's node is an isolated vertex... it's useless, remove it.
    if nx.is_isolate(flow, dependee_node):
      flow.remove_node(dependee_node)
    if nx.is_isolate(flow, dependency_node):
      flow.remove_node(dependency_node)

  # Add the actual dependency edges between the files.
  for dependency_edge in cycle_file_graph.edges:
    flow.add_edge(dependency_edge[0] + ' ->',
                  '-> ' + dependency_edge[1],
                  capacity=1)

  return flow


def get_modules_circular_dependency(module_map, dependency_map):
  """
  """

  def _map_to_dependencies(module):
    """
    Helper function to create a dictionary key mapping :param module: to its
    dependencies.
    """
    return (module,
            # Return the dependencies as a list, sorted, as opposed to a set,
            # so the order is deterministic.
            list(sorted(module_map.get_dependencies_of_module(module))))

  dependencies = dict(map(_map_to_dependencies, module_map))
  graph = nx.DiGraph(dependencies)
  if nx.is_directed_acyclic_graph(graph):
    return True

  cycles = list(nx.simple_cycles(graph))
  smallest_cycles_length = min([len(c) for c in cycles])
  smallest_cycles = list(
    filter(lambda l: len(l) == smallest_cycles_length, cycles))
  # "simple_cycles" isn't deterministic on the "inner" order of the result -
  # the order of nodes in the cycle. To make the results more reproducible
  # and debuggable, we sacrifice some CPU time here to keep a consistent order.
  util.rotate_list_of_cycles(smallest_cycles)

  # Now create an alphanumeric order of the cycles which respects every
  # element, so the list is ordered based on sublists' 1st element, then
  # within each group the 2nd, etc.
  smallest_cycles.sort(key=lambda l: ','.join(l))

  print("Found %d smallest cycles of length %d between modules."
        % (len(smallest_cycles), smallest_cycles_length))

  for i, cycle in tqdm(enumerate(smallest_cycles),
                       desc="Breaking cycles...",
                       total=len(smallest_cycles),
                       unit='cycle'):
    # Make sure it is "actually" a cycle.
    cycle.append(cycle[0])

    tqdm.write("Circular dependency between modules found on the following "
               "path:\n"
               "    %s" % ' -> '.join(cycle))

    # Create a graph that contains the files that span the dependencies that
    # resulted in the cycle.
    cycle_file_graph = nx.DiGraph()
    for module_A, module_B in itertools.zip_longest(cycle[:-1], cycle[1:]):
      # (E.g. iterates A -> B, B -> C, C -> A)

      tqdm.write("Between modules %s -> %s, the following files include each "
                 "other:" % (module_A, module_B))
      files = dependency_map.get_files_creating_dependency_between(module_A,
                                                                   module_B)
      for file_in_A, files_in_B in files.items():
        files[file_in_A] = list(files_in_B)  # Set to list transformation.
        for file_in_B in files_in_B:
          tqdm.write("%s: %s" % (file_in_A, file_in_B))
          cycle_file_graph.add_edge(file_in_A, file_in_B)

    # Map every file that spans the circular dependency to the module they
    # belong to.
    module_to_files_map = module_map.filter_modules_for_fragments(
      cycle_file_graph.nodes)

    # QUESTION: It looks like this early "return" is not needed, as the
    #           dependency cut thing seems to give valueable results here too.
    # if nx.is_weakly_connected(cycle_file_graph):
    #   tqdm.write("Fatal error! The dependency graph for circular module "
    #              "dependency\n"
    #              "    %s\n"
    #              "is fully connected. Modules cannot be split."
    #              % ' -> '.join(cycle),
    #              file=sys.stderr)
    #   tqdm.write("The dependencies that create the cycle is spanned by the "
    #              "following files:", file=sys.stderr)
    #   tqdm.write(json.dumps(nx.to_dict_of_lists(cycle_file_graph), indent=2),
    #              file=sys.stderr)
    #
    #   # graph_visualisation.draw_dependency_graph(cycle_file_graph,
    #   #                                           module_to_files_map)
    #   # # (Blocking call here.)
    #   # plt.show()
    #   # TODO: Record the fact that resolving the dependency is impossible!
    #   continue

    flow = _create_flow_for_cycle_graph(cycle, cycle_file_graph,
                                        module_to_files_map)
    # Calculate the minimal cut on the built flow-graph.
    cut_value, partition = nx.minimum_cut(flow,
                                          cycle[0] + ' ->', '-> ' + cycle[0])

    tqdm.write("A cut of value %d, with the partitions:" % cut_value)
    tqdm.write(json.dumps((list(partition[0]), list(partition[1])),
                          indent=2))

    graph_visualisation.draw_flow_and_cut(flow, cycle_file_graph,
                                          module_to_files_map, cycle[0],
                                          partition)
    # (Blocking call here!)
    plt.show()

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

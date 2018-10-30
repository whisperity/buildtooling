import codecs
import itertools
import json
import os
import re
import sys
from collections import Counter, deque
from operator import itemgetter

import matplotlib.pyplot

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

  def _rotate_cycles(lst):
    """
    Helper function to rotate a list of cycles represented as lists.
    "simple_cycles" isn't deterministic on the "inner" order of the result -
    the order of nodes in the cycle. To make the results more reproducible
    and debuggable, we sacrifice some CPU time here to keep a consistent order.
    """
    for i, c in enumerate(lst):
      common_prefix = os.path.commonprefix(c)
      sort_based_on_char_idx = len(common_prefix)

      # Expand the strings in the list so the sort character index is always
      # in range. (' ' < any alphanumerical letter)
      expand = list(map(lambda s: s.ljust(sort_based_on_char_idx + 1), c))

      # We must not just sort the list because this list represents an ordered
      # cycle in the graph! Instead, rotate that the "smallest" key is the
      # first.
      min_idx, _ = min(enumerate(expand), key=itemgetter(1))
      d = deque(expand)
      d.rotate(-min_idx)

      lst[i] = list(map(lambda s: s.strip(), d))

  def _draw_dependency_graph(cycle_graph, module_to_file_map):
    """
    Helper function that creates a visualisation graph of the includes in the
    :param cycle_graph:.
    """
    COLOURS = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
               '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe',
               '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000',
               '#aaffc3', '#808000', '#ffd8b1', '#000075', '#808080']

    # To be able to colour individual files belonging to the same module with
    # the same colour, this map is needed.

    pos = nx.nx_pydot.graphviz_layout(cycle_graph)
    for idx, item in enumerate(module_to_file_map.items()):
      module, files = item
      nx.draw_networkx_nodes(cycle_graph, pos,
                             nodelist=files,
                             node_color=COLOURS[idx])
      nx.draw_networkx_edges(cycle_graph, pos,
                             edgelist=cycle_graph.out_edges(files),
                             edge_color=COLOURS[idx])

    nx.draw_networkx_labels(cycle_graph, pos)
    matplotlib.pyplot.axis('off')

    # (Blocking call here.)
    matplotlib.pyplot.show()

  dependencies = dict(map(_map_to_dependencies, module_map))
  graph = nx.DiGraph(dependencies)
  if nx.is_directed_acyclic_graph(graph):
    return True

  cycles = list(nx.simple_cycles(graph))
  smallest_cycles_length = min([len(c) for c in cycles])
  smallest_cycles = list(
    filter(lambda l: len(l) == smallest_cycles_length, cycles))
  _rotate_cycles(smallest_cycles)

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

    cycle_file_graph = nx.DiGraph()
    for module_A, module_B in itertools.zip_longest(cycle[:-1], cycle[1:]):
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
    module_to_file = module_map.filter_modules_for_fragments(
      cycle_file_graph.nodes)

    # Create a flow graph that has a node for each module in the cycle,
    # mapping the files belonging to a module with a directed edge, and also
    # containing the dependency edges.
    # If a file is dependent upon and also depends on others, it is added
    # multiple times, once for the incoming, and once for the outgoing edges.
    flow = nx.DiGraph()

    # Handle the source and sink of the dependency graph.
    flow.add_node(cycle[0] + ' ->')
    flow.add_node('-> ' + cycle[0])
    for file_in_module in module_to_file[cycle[0]]:
      if cycle_file_graph.out_degree(file_in_module) > 0:
        # file_in_module depends on other files.
        flow.add_node(file_in_module + ' ->')
        flow.add_edge(cycle[0] + ' ->',
                      file_in_module + ' ->')  # capacity: infinite
      if cycle_file_graph.in_degree(file_in_module) > 0:
        # file_in_module is a dependency of other files.
        flow.add_node('-> ' + file_in_module)
        flow.add_edge('-> ' + file_in_module,
                      '-> ' + cycle[0])  # capacity: infinite

    # Handle the inner nodes of the cycle.
    for module in cycle[1:-1]:
      for file_in_module in module_to_file[module]:
        in_degree = cycle_file_graph.in_degree(file_in_module)
        out_degree = cycle_file_graph.out_degree(file_in_module)

        if out_degree > 0:
          # file_in_module depends on other files.
          flow.add_node(file_in_module + ' ->')

        if in_degree > 0:
          # file_in_module is a dependency of other files.
          flow.add_node('-> ' + file_in_module)

        if in_degree > 0 and out_degree > 0:
          # If the file is both a dependency and depends on others, link the
          # two nodes.
          flow.add_edge('-> ' + file_in_module,
                        file_in_module + ' ->',
                        capacity=1)

    # Add the actual dependency edges between the files.
    for dependency_edge in cycle_file_graph.edges:
      flow.add_edge(dependency_edge[0] + ' ->',
                    '-> ' + dependency_edge[1],
                    capacity=1)

    def _visualise_flow_and_cut(idx, cycle_start, partition):
      """
      Helper function to visualise the flow graph and mark the cut created by
      :param partition:.
      """
      pos = nx.nx_pydot.graphviz_layout(flow)
      matplotlib.pyplot.figure(idx)

      COLOURS = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
                 '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe',
                 '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000',
                 '#aaffc3', '#808000', '#ffd8b1', '#000075', '#808080']
      module_to_colour = {}

      # Draw the module node of the cycle's two ends.
      nx.draw_networkx_nodes(flow, pos,
                             nodelist=[cycle_start + ' ->',
                                       '-> ' + cycle_start],
                             node_color=COLOURS[0],
                             node_shape='s')

      nx.draw_networkx_labels(flow, pos,
                              labels=dict(
                                map(lambda e:
                                    (e, e.replace(' ->', '')
                                     .replace('-> ', '')),
                                    [cycle_start + ' ->',
                                     '-> ' + cycle_start])),
                              font_color='black')

      for i, module in enumerate(sorted(module_to_file.keys())):
        module_to_colour[module] = COLOURS[i]

        # Draw the file nodes belonging to the iterated module.
        dependees = list(filter(lambda e: e in flow.nodes,
                                map(lambda s: s + ' ->',
                                    module_to_file[module])))
        dependencies = list(filter(lambda e: e in flow.nodes,
                                   map(lambda s: '-> ' + s,
                                       module_to_file[module])))

        nx.draw_networkx_nodes(flow, pos,
                               nodelist=dependees + dependencies,
                               node_color=COLOURS[i])
        nx.draw_networkx_labels(flow, pos,
                                labels=dict(
                                  map(lambda e:
                                      (e, e.replace(' ->', '')
                                           .replace('-> ', '')),
                                      dependees + dependencies)),
                                font_color='#666666')

        if module == cycle_start:
          # ... and link them to the module node (in case of cycle's two end)
          for dep in dependees:
            if (module + ' ->', dep) in flow.edges:
              nx.draw_networkx_edges(flow, pos,
                                     edgelist=[(module + ' ->', dep)],
                                     edge_color='#bbbbbb')

          for dep in dependencies:
            if (dep, '-> ' + module) in flow.edges:
              nx.draw_networkx_edges(flow, pos,
                                     edgelist=[(dep, '-> ' + module)],
                                     edge_color='#bbbbbb')
        else:
          # Or link them to each other, if the file appears on both sides
          # of the module.
          for file_in_module in module_to_file[module]:
            self_edge = ('-> ' + file_in_module, file_in_module + ' ->')
            if self_edge in flow.edges:
              nx.draw_networkx_edges(flow, pos,
                                     edgelist=[self_edge],
                                     edge_color='#222222')

      # Draw in the file dependencies.
      def _draw_edge(u, v):
        # Show the cut's edges in a different style. A cutting edge is an
        # edge which ends are in different partitions.
        S, T = partition[0], partition[1]
        if (u in S and v in T) or (u in T and v in S):
          # colour = '#b33a3a'
          colour = '#ffa500'
          width = 4.0
          style = 'dashdot'
        else:
          from_module = next(module_map.get_modules_for_fragment(
            u.replace(' ->', '')), None)
          colour = module_to_colour[from_module]
          width = 1.0
          style = 'solid'

        nx.draw_networkx_edges(flow, pos,
                               edgelist=[(u, v)],
                               width=width,
                               edge_color=colour,
                               style=style)

      for dependency_edge in cycle_file_graph.edges:
        _draw_edge(dependency_edge[0] + ' ->', '-> ' + dependency_edge[1])

      matplotlib.pyplot.axis('off')

    # Calculate the minimal cut on the built flow-graph.
    cut_value, partition = \
      nx.minimum_cut(flow, cycle[0] + ' ->', '-> ' + cycle[0])

    _visualise_flow_and_cut(i + 1, cycle[0], partition)
    matplotlib.pyplot.show()

    if nx.is_weakly_connected(cycle_file_graph):
      print("Fatal error! The dependency graph for circular module "
            "dependency\n"
            "    %s\n"
            "is fully connected. Modules cannot be split."
            % ' -> '.join(cycle),
            file=sys.stderr)
      print("The dependencies that create the cycle is spanned by the "
            "following files:", file=sys.stderr)
      print(json.dumps(nx.to_dict_of_lists(cycle_file_graph), indent=2),
            file=sys.stderr)
      _draw_dependency_graph(cycle_file_graph)
      # TODO: Just fail here quickly if we fixed handling single components.
      # return False

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

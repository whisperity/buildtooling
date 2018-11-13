import codecs
import itertools
import os
import re
import sys
from collections import Counter
from hashlib import md5
from operator import itemgetter

try:
  import matplotlib.pyplot as plt
  import networkx as nx
except ImportError as e:
  print("Error! A dependency of this tool could not be satisfied. Please "
        "install the following Python package via 'pip' either to the "
        "system, or preferably create a virtualenv.")
  raise

from utils import strip_folder, walk_folder
from utils import graph
from utils.graph import generate_cutting_edges
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

  def remove_fragment(self, fragment_file):
    """
    Unmaps the given :param fragment_file: from all modules it is mapped to.
    """
    modules_gone_empty = list()
    for module in self.filter_modules_for_fragments([fragment_file]):
      self._map[module]['fragments'].remove(fragment_file)
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
        # print("FOUND FILE TO REMOVE IN A MODULE", filename)
        del self._map[module][filename]
        if not self._map[module]:
          # The module has emptied out.
          modules_to_remove.append(module)
        continue

      # print("MODULE", module)
      files_to_remove_from_module = list()
      for file_in_module in self._map[module]:
        # print("FILE IN MODULE", module, file_in_module)
        inner_modules_to_remove = list()
        for dep_module, dep_filelist in \
              self._map[module][file_in_module].items():
          if filename in dep_filelist:
            # Remove the file from every file's dependency list, if found.
            # print("FOUND FILE TO REMOVE AS DEPENDENCY", filename)
            dep_filelist.remove(filename)
            if not dep_filelist:
              # The dependency list of module 'dep_module' for
              # 'file_in_module' has emptied out, remove this entry.
              inner_modules_to_remove.append(dep_module)

        for remove_module in inner_modules_to_remove:
          # Clear module-level dependency if now in fact the file does not
          # depend on said module anymore.
          # print("MODULE", remove_module, "AS DEPENDENCY EMPTIED")
          del self._map[module][file_in_module][remove_module]

        if not self._map[module][file_in_module]:
          # print("DEPENDENCY LIST OF", module, file_in_module, "EMPTIED.")
          files_to_remove_from_module.append(file_in_module)

      for remove_from_module in files_to_remove_from_module:
        # print("DEPENDENCY LIST OF", remove_from_module, "EMPTY... DELETING "
        #       "FILE")
        del self._map[module][remove_from_module]

    for remove_module in modules_to_remove:
      # print("MODULE", remove_module, "NO LONGER CONTAINS ANY FILES THAT "
      #       "DEPEND... REMOVING.")
      del self._map[remove_module]

  def get_dependencies(self, filename):
    """
    :return: A collection of files :param filename: depends on, across every
    module.
    """
    ret = set()
    modules = self._module_mapping.get_modules_for_fragment(filename)

    for mod in modules:
      if mod not in self._map:
        continue
      if filename not in self._map[mod]:
        continue

      for dependency_module in self._map[mod][filename]:
        ret.update(set(self._map[mod][filename][dependency_module]))

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
          if filename in self._map[mod][dependee_file][dependee_module]:
            ret.add(dependee_file)

    return ret

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

  def synthesize_intermodule_imports(self):
    """
    Using the dependencies stored in the current instance, synthesize a
    module-module 'import' list into the :var _module_mapping: of the instance.
    """
    for module in self._module_mapping:
      self._module_mapping.clear_module_imports(module)

    for module in self._map:
      module_dependencies = set()
      for file_entry in self._map[module].values():
        module_dependencies.update(file_entry.keys())
      module_dependencies.discard(module)

      for dependency in module_dependencies:
        self._module_mapping.add_module_import(module, dependency)


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

    if module != cycle[0]:
      # If all files for a module had been added and every such file appeared
      # "on both sides" (both as a dependency and one that depends on others),
      # then the module's node is an isolated vertex... it's useless, remove
      # it.
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


# FIXME: Introduce a method transforming file-to-node and node-to-file (->).


def _files_from_cutting_edges(module_map, flow_graph, cutting_edges):
  """
  Using the given :param module_map: and :param flow_graph:, which has been cut
  at the dependency (!) edges :param cutting_edges:, create a dict of files
  and module names for files that should be moved into new modules.
  """

  # First, consider the files that are the endpoints of the cutting edges
  # for the move. This is generally a good heuristic as it tends to "break"
  # a lot of cycle chance, e.g. when 20 files depend on a file and one of
  # these dependencies create the cycle.
  files_to_move = dict(map(lambda e:
                           (e[1].replace('-> ', '').replace(' ->', ''), None),
                           cutting_edges))

  # However, it could be that a file on the end of the cutting edge is also a
  # file from which dependencies are made. This can cause that a file
  # belonging to module A is moved to module B, but the cycle in itself is not
  # broken, as another iteration of the algorithm will find a B -> ... -> B
  # cycle. In case of these files, it is more beneficial to move the
  # dependee instead.
  for file in list(files_to_move):
    if file + ' ->' in flow_graph.nodes and '-> ' + file in flow_graph.nodes:
      # Move the files that are the starting points of edges leading into the
      # previously marked files.
      try:
        paths = list(nx.all_shortest_paths(flow_graph,
                                           file + ' ->',
                                           '-> ' + file))
      except nx.NetworkXNoPath:
        paths = []

      del files_to_move[file]
      cut_candidates = list(set(map(
        lambda e: e[0].replace('-> ', '').replace(' ->', ''),
        filter(lambda e: file in e[1], cutting_edges))))

      # Iterate as long as we have other termini of cutting.
      while cut_candidates:
        new_move_candidate = cut_candidates[0]
        del cut_candidates[0]
        files_to_move[new_move_candidate] = None

        if '-> ' + new_move_candidate in flow_graph.nodes and \
              new_move_candidate + ' ->' in flow_graph.nodes:
          # The "source" terminus of the cutting edge leading into a file that
          # is both a dependee and a dependency is *also* both a dependee and
          # a dependency.
          # In this case, the dependency graph cannot be reasonably broken by
          # moving the "source" file either, as the chain would still be there
          # via the new module's name.
          try:
            candidates_paths = list(nx.all_shortest_paths(
              flow_graph,
              new_move_candidate + ' ->',
              '-> ' + new_move_candidate))
          except nx.NetworkXNoPath:
            candidates_paths = []

          if not any(new_move_candidate + ' ->' in path
                     for path in paths) \
                and not any(file + ' ->' in path
                            for path in candidates_paths):
            # If the inner file is also a dependee and a dependency, but the
            # files are not part of the paths between the "dependee" and
            # "dependency" sides of each otherthen put this file into
            # *another* different module.
            # This won't fix the cycles either, but will make the next
            # iteration work with a much smaller graph.
            files_to_move[new_move_candidate] = _get_new_module_name(
              module_map, [new_move_candidate])
          else:
            # The move candidate is part of a path between the insolvent
            # dependency. Try to see if other nodes in the path could be
            # moved...
            del files_to_move[new_move_candidate]

            def _handle_direction(generator):
              """
              Helper function to check in a graph traversing
              :param generator: if candidate files to move could be found.
              """
              found_any = False
              for group_in_direction in generator:
                for file in group_in_direction:
                  file = file.replace('-> ', '').replace(' ->', '')

                  if not ('-> ' + file
                          in flow_graph.nodes and file + ' ->'
                          in flow_graph.nodes) and \
                        '-> ' + file + ' ->' not in flow_graph.nodes:
                    # If the found file is not BOTH a dependee and a dependency
                    # (as in that case moving it would yet again just rename
                    # the module in the cycle but won't fix the cycle...), and
                    # is also *NOT* a node that represents a module.
                    cut_candidates.insert(0, file)
                    found_any = True
                if found_any:
                  return True
              return False

            found_any = _handle_direction(
              graph.transitive_leveled_successors(
                flow_graph, new_move_candidate + ' ->'))
            if not found_any:
              _handle_direction(graph.transitive_leveled_predecessors(
                flow_graph, '-> ' + new_move_candidate))

  # Get the files which were marked for moving but no new module name was
  # generated for them yet, and name them to an automatic module name.
  files_moving_without_new_module_name = list(
    map(
      lambda e: e[0],
      filter(lambda e: e[1] is None,
             files_to_move.items())))
  new_module_name = _get_new_module_name(module_map,
                                         files_moving_without_new_module_name)
  for file in files_moving_without_new_module_name:
    files_to_move[file] = new_module_name

  return files_to_move


def _get_new_module_name(module_map, moved_files):
  """
  Given a :param module_map: this function generated a name for files in
  :param moved_files:. The new module name will be something that does not
  exist in the module map already.
  """
  if len(moved_files) == 0:
    return None

  digest = md5(','.join(moved_files).encode('utf-8')).hexdigest()
  digest_sublen = 7
  new_name = "Module__autogen_%s" % digest[:digest_sublen]
  while new_name in module_map:
    digest_sublen += 1
    if digest_sublen > len(digest):
      raise IndexError("Hash length of %d exhausted" % len(digest))
    new_name = "Module__autogen_%s" % digest[:digest_sublen]

  return new_name


def get_circular_dependency_resolution(module_map, dependency_map):
  """
  Checks if the given :param module_map: and :param dependency_map: (which is
  created bound to the :param module_map:) contain circular dependencies on
  the module "folder" level.

  :return: A map of files to new module names to be moved to resolve the
  dependency. The map is empty if no cycles were found.
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

  file_to_new_module = dict()

  dependencies = dict(map(_map_to_dependencies, module_map))
  graph = nx.DiGraph(dependencies)
  if nx.is_directed_acyclic_graph(graph):
    # If the dependency graph no longer contains any cycles, there is nothing
    # to resolve.
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

    flow = _create_flow_for_cycle_graph(cycle, cycle_file_graph,
                                        module_to_files_map)
    cut_settled = False
    while not cut_settled:
      # Calculate the minimal cut on the built flow-graph.
      cut_value, partition = nx.minimum_cut(flow,
                                            cycle[0] + ' ->',
                                            '-> ' + cycle[0])

      # Create edges from the file dependency graph in which the edge
      # endpoints show the "direction" of the edge. (Partition contains edges
      # between nodes named as such.)
      cycle_file_graph_edges_namedirected = map(lambda e: (e[0] + ' ->',
                                                           '-> ' + e[1]),
                                                cycle_file_graph.edges)
      cycle_file_graph_edges_namedirected = filter(
        lambda e: e in flow.edges, cycle_file_graph_edges_namedirected)

      cutting_edges = list(
        generate_cutting_edges(cycle_file_graph_edges_namedirected, partition))

      # Try fetching the list of files to move based on the cut.
      files_to_move = _files_from_cutting_edges(module_map,
                                                flow,
                                                cutting_edges)

      if not files_to_move:
        # If files_to_move is a falsy value, like empty set, the cycle is
        # deemed infeasible to solve.
        return False
      else:
        # Update the list of files that are to be moved into new modules to
        # solve this cycle, and go for the next.
        cut_settled = True
        file_to_new_module.update(files_to_move)

  return file_to_new_module


def apply_file_moves(module_map, dependency_map, moved_files):
  """
  Update :param ModuleMapping: and :type DependencyMap: by applying the file
  moving to other module changes dictated by :param moved_files:.
  """
  if not moved_files:
    return

  dependencies_to_fix_up = list()
  for filename in moved_files:
    for file_depending_on_moved in dependency_map.get_dependees(filename):
      dependencies_to_fix_up.append((file_depending_on_moved, filename))
    for moved_depending_on_file in dependency_map.get_dependencies(filename):
      dependencies_to_fix_up.append((filename, moved_depending_on_file))

    dependency_map.remove_file(filename)

  for filename, new_module in moved_files.items():
    module_map.remove_fragment(filename)
    if new_module not in module_map:
      module_map.add_module(new_module, os.devnull)
    module_map.add_fragment(new_module, filename)

  for dependee, dependency in dependencies_to_fix_up:
    # Fix the dependency map so the file->file dependencies now point through
    # the new module names.
    dependency_map.add_dependency(dependee, dependency)

  # Resynthesize the import list because file-module relations have changed.
  dependency_map.synthesize_intermodule_imports()


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

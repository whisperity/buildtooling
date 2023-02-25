import itertools
import multiprocessing
import operator
import sys
from collections import Counter, deque

try:
  import networkx as nx
except ImportError as e:
  print("Error! A dependency of this tool could not be satisfied. Please "
        "install the following Python package via 'pip' either to the "
        "system, or preferably create a virtualenv.")
  raise

from ModulesTSMaker import mapping, util
from utils import graph, logging
from utils.graph_visualisation import get_visualizer as graph_visualisation


DESCRIPTION = "Solve potential module import cycles by splitting modules"


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
  for file in sorted(files_to_move):
    # Iterate copy of the initial files, the dict is modified in the iteration.
    logging.verbose(" ? File candidate for moving: %s" % file)
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
      logging.verbose(" ! File cannot be moved: %s" % file)
      cut_candidates = deque(sorted(set(map(
        lambda e: e[0].replace('-> ', '').replace(' ->', ''),
        filter(lambda e: file in e[1], cutting_edges)))))

      # Iterate as long as we have other termini of cutting.
      while cut_candidates:
        new_move_candidate = cut_candidates.popleft()
        logging.verbose(" ? File candidate for moving: %s"
                        % new_move_candidate)
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
            files_to_move[new_move_candidate] = mapping.get_new_module_name(
              module_map, [new_move_candidate])
          else:
            # The move candidate is part of a path between the insolvent
            # dependency. Try to see if other nodes in the path could be
            # moved...
            logging.verbose(" ! File cannot be moved: %s"
                            % new_move_candidate)
            del files_to_move[new_move_candidate]

            def _handle_direction(generator):
              """
              Helper function to check in a graph traversing
              :param generator: if candidate files to move could be found.
              """
              found_any = False
              for group_in_direction in generator:
                for file in sorted(group_in_direction):
                  file = file.replace('-> ', '').replace(' ->', '')

                  if not ('-> ' + file
                          in flow_graph.nodes and file + ' ->'
                          in flow_graph.nodes) and \
                        '-> ' + file + ' ->' not in flow_graph.nodes:
                    # If the found file is not BOTH a dependee and a dependency
                    # (as in that case moving it would yet again just rename
                    # the module in the cycle but won't fix the cycle...), and
                    # is also *NOT* a node that represents a module.
                    # In this case, we mark this file as the next candidate.
                    cut_candidates.append(file)
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
  new_module_name = mapping.get_new_module_name(
    module_map, sorted(files_moving_without_new_module_name))
  for file in files_moving_without_new_module_name:
    files_to_move[file] = new_module_name

  logging.verbose("Will move the following files to fix the cycle:")
  if logging.get_configuration()["verbose"]:
    for file, module in files_to_move.items():
      logging.verbose("    %s -> %s" % (file, module))

  return files_to_move


def _parallel(cycle, module_map, dependency_map):
  """
  The parallel worker part of :func get_circular_dependency_resolution:.
  """

  # Make sure it is "actually" a cycle.
  cycle.append(cycle[0])

  logging.verbose("----------------------------------------------------------")
  logging.verbose("Circular dependency between modules found on the following "
                  "path:\n    %s" % ' -> '.join(cycle))

  # Create a graph that contains the files that span the dependencies that
  # resulted in the cycle.
  cycle_file_graph = nx.DiGraph()
  for module_A, module_B in itertools.zip_longest(cycle[:-1], cycle[1:]):
    # (E.g. iterates A -> B, B -> C, C -> A)

    logging.verbose("Between modules %s -> %s, the following files include "
                    "each other:" % (module_A, module_B))
    files = dependency_map.get_files_creating_dependency_between(module_A,
                                                                 module_B)
    for file_in_A, files_in_B in sorted(files.items()):
      # Cast away the dependency's "kind" value.
      files[file_in_A] = sorted(t[0] for t in files_in_B if t[1] == 'uses')
      if not files[file_in_A]:
        # If the file on the left side (file_in_A) does not participate in
        # dependency resolution because it doesn't uses-depend on anything,
        # skip it.
        continue

      logging.verbose("    %s:" % file_in_A)
      logging.verbose("        %s" % '\n        '.join(files[file_in_A]))
      cycle_file_graph.add_edges_from(zip(itertools.repeat(file_in_A),
                                          files[file_in_A]))

  # Map every file that spans the circular dependency to the module they
  # belong to.
  module_to_files_map = module_map.filter_modules_for_fragments(
    cycle_file_graph.nodes)

  graph_visualisation('dependencies').draw_dependency_graph(
    cycle_file_graph, module_to_files_map)
  graph_visualisation('dependencies').show()  # Blocking call!

  flow = _create_flow_for_cycle_graph(cycle, cycle_file_graph,
                                      module_to_files_map)

  # Calculate the minimal cut on the built flow-graph.
  cut_value, partition = nx.minimum_cut(flow,
                                        cycle[0] + ' ->',
                                        '-> ' + cycle[0])

  graph_visualisation('cuts').draw_flow_and_cut(
    flow, cycle_file_graph, module_to_files_map, cycle[0], partition)
  graph_visualisation('cuts').show()  # Blocking call!

  # Create edges from the file dependency graph in which the edge
  # endpoints show the "direction" of the edge. (Partition contains edges
  # between nodes named as such.)
  cycle_file_graph_edges_namedirected = map(lambda e: (e[0] + ' ->',
                                                       '-> ' + e[1]),
                                            cycle_file_graph.edges)
  cycle_file_graph_edges_namedirected = filter(
    lambda e: e in flow.edges, cycle_file_graph_edges_namedirected)

  cutting_edges = list(
    graph.generate_cutting_edges(cycle_file_graph_edges_namedirected,
                                 partition))

  # Try fetching the list of files to move based on the cut.
  files_to_move = _files_from_cutting_edges(module_map,
                                            flow,
                                            cutting_edges)

  if not files_to_move:
    # If files_to_move is a falsy value, like empty set, the cycle is
    # deemed infeasible to solve.
    return False
  else:
    # Return the list of files to be cut for merging to the pool handler.
    return files_to_move


def get_circular_dependency_resolution(iteration_pingpong_buffer,
                                       iteration_pingpong_threshold,
                                       pool,
                                       module_map,
                                       dependency_map):
  """
  Checks if the given :param module_map: and :param dependency_map: (which is
  created bound to the :param module_map:) contain circular dependencies on
  the module "folder" level.

  :param iteration_pingpong_buffer: A buffer to store dependency cycles in a
  circular resolution detection lookbehind approximator. If the same cycle
  appears twice in this buffer, the algorithm is considered to have stuck in
  a loop.

  :param pool: A :type multiprocessing.Pool: on which the cycle resolution
  should be executed. Individual cycles can be resolved in an parallel manner,
  as resolution is only calculated, and not applied to the shared resources.

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
            sorted(module_map.get_dependencies_of_module(module)))

  logging.normal("... Searching for cycles between %d modules ..."
                 % len(module_map))
  dependencies = dict(map(_map_to_dependencies, module_map))
  shortest_cycle_length, minimum_long_cycles = graph.simple_cycles(
      dependencies)
  # minimum_long_cycles return a dict(Node, [Node, Node2, Node3, ..., Node])
  # format, associating each module with an edge that contains the associated
  # edge both as a prefix and a suffix. Cut this out to a simple
  # [Node, Node2, ...] list instead.
  cycles = list(map(lambda pair: pair[1][:-1], minimum_long_cycles))
  if not cycles:
    # If the dependency graph no longer contains any cycles, there is nothing
    # to resolve.
    return True

  # The found cycle list isn't deterministic on the "inner" order of the result
  # the order of nodes in the cycle. To make the results more reproducible
  # and debuggable, we sacrifice some CPU time here to keep a consistent order.
  util.rotate_list_of_cycles(cycles)

  # The exact same cycle might be repeating at this point, and while it was
  # previously hard to detect because it could have been A->B->C and B->C->A
  # and C->A->B in the result, after rotation, now it's
  # [A->B->C, A->B->C, A->B->C].
  cycles = list(set([','.join(cycle) for cycle in cycles]))

  # Now create an alphanumeric order of the cycles which respects every
  # element, so the list is ordered based on sublists' 1st element, then
  # within each group the 2nd, etc.
  cycles.sort()
  iteration_pingpong_buffer.extend(cycles)
  cycles = [cycle.split(',') for cycle in cycles]

  logging.normal("Found %d smallest cycles of length %d between modules."
                 % (len(cycles), shortest_cycle_length))

  args = zip(cycles,
             itertools.repeat(module_map),
             itertools.repeat(dependency_map))

  ret = dict()
  for result in pool.starmap(_parallel, args):
    if result is False:
      return False
    ret.update(result)

  if iteration_pingpong_buffer:
    iteration_pingpong_check = next(iter(Counter(iteration_pingpong_buffer)
                                         .most_common(1)),
                                    None)
    if iteration_pingpong_check and \
          iteration_pingpong_check[1] > iteration_pingpong_threshold:
        # Found the same cycle twice in the lookbehind buffer - consider the
        # algorithm looping...
        logging.essential("Error! The same cycle appeared %d times amongst "
                          "the last %d handled cycles.\nConsidering the "
                          "algorithm to have stuck in a loop!\n%s"
                          % (iteration_pingpong_check[1],
                             len(iteration_pingpong_buffer),
                             iteration_pingpong_check[0]), file=sys.stderr)
        logging.essential("The offending file moves in the current step, "
                          "likely continuing the cycle were: ")
        for file, module in ret.items():
          logging.essential("    %s -> %s" % (file, module))

        raise RecursionError()

  return ret


def main(MODULE_MAP, DEPENDENCY_MAP,
         THREAD_COUNT, MODULE_SPLIT_PINGPONG_THRESHOLD):
  # Make sure the module-to-module import directives are in the dependency map,
  # as this stage operates based on them.
  DEPENDENCY_MAP.synthesize_intermodule_imports()

  pingpong_buffer = deque([], MODULE_SPLIT_PINGPONG_THRESHOLD ** 2)

  # Check if the read module map contains circular dependencies that make the
  # current module map infeasible, and try to resolve it.
  # It is to be noted that this algorithm is finite, as worst case the system
  # will fall apart to N distinct modules where N is the number of translation
  # units -- unfortunately there was no improvement on modularisation made in
  # this case...
  iteration_count = 1
  with multiprocessing.Pool(THREAD_COUNT) as pool:
    while True:
      logging.essential(
        "========->> Begin iteration %d trying to break cycles.. <<-========"
        % iteration_count)

      files_to_move = get_circular_dependency_resolution(
        pingpong_buffer, MODULE_SPLIT_PINGPONG_THRESHOLD,
        pool, MODULE_MAP, DEPENDENCY_MAP)
      if files_to_move is False:
        logging.essential("Error! The modules contain circular dependencies "
                          "on each other which cannot be resolved "
                          "automatically by splitting them.",
                          file=sys.stderr)
        sys.exit(1)
      elif files_to_move is True:
        # If the resolution of the cycles is to do nothing, there are no issues
        # with the mapping anymore.
        logging.normal("Nothing to do.")
        break
      else:
        # Alter the module map with the calculated moves, and try running the
        # iteration again.
        mapping.apply_file_moves(MODULE_MAP, DEPENDENCY_MAP, files_to_move)

      iteration_count += 1

  mapping.fix_module_names(MODULE_MAP, DEPENDENCY_MAP)

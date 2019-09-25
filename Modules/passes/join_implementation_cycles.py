from itertools import zip_longest
from operator import itemgetter

try:
  import networkx as nx
except ImportError as e:
  print("Error! A dependency of this tool could not be satisfied. Please "
        "install the following Python package via 'pip' either to the "
        "system, or preferably create a virtualenv.")
  raise

from ModulesTSMaker import mapping
from utils import logging
from utils.graph_visualisation import get_visualizer as graph_visualisation


DESCRIPTION = "Solve dependency cycles by merging module contents"


def _fold_cycles(module_map, dependency_map):
  """
  Executes the folding of cyclical dependencies into a new merged module.

  :return: A dict of modules the merge (in the format of ret[k] is a list, and
  modules in this list should be merged into k). If no merges are necessary,
  return explicit True.
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

  dependencies = dict(map(_map_to_dependencies, module_map))
  graph = nx.DiGraph(dependencies)

  # Generating the simple_cycles() of the dependency graph is very very costly
  # at this point, as for ~60 modules they could be the order of or above
  # 10 billion. Instead, this quadratic algorithm of the adjacency matrix will
  # try selecting shortest cycles.
  dependency_paths = dict()
  for n in sorted(dependencies):
    for m in sorted(dependencies):
      if n == m:
        continue

      try:
        forward_path = next(nx.shortest_simple_paths(graph, n, m))
        backward_path = next(nx.shortest_simple_paths(graph, m, n))
      except nx.NetworkXNoPath:
        # Disregard the exception if a module cannot be reached from another
        # one.
        continue

      # Cut the repeated middle element.
      cycle = forward_path + backward_path[1:]
      if n not in dependency_paths or len(cycle) < len(dependency_paths[n]):
        dependency_paths[n] = cycle

  if not dependency_paths:
    # If there are no more cycles, quit.
    return True

  cycle_lengths = sorted(
    map(lambda e: (e[0], len(e[1])), dependency_paths.items()),
    key=itemgetter(1))
  cycle_lengths_minimum = min(cycle_lengths, key=itemgetter(1))[1]
  minimum_long_cycles = sorted(filter(
    lambda e: len(e[1]) == cycle_lengths_minimum,
    dependency_paths.items()))

  logging.normal("Found %d shortest cycles with the length of %d, trying to "
                 "merge..." % (len(minimum_long_cycles),
                               cycle_lengths_minimum))

  modules_marked_for_moving = set()
  modules_to_merge = dict()  # k -> [v]: List of modules to merge into 'k'.
  coupling_strength_collected = list()
  for _, cycle in minimum_long_cycles:
    # For every cycle detected, try folding it towards the left. Each iteration
    # does one fold on every cycle.
    logging.verbose("\nCircular dependency between modules found on the "
                    "following path:\n    %s" % cycle[0], end='')

    # Calculate the coupling strength between the modules in the cycle.
    coupling_strength = dict()
    for module_A, module_B in zip_longest(cycle[:-1], cycle[1:]):
      # (E.g. iterates A -> B, B -> C, C -> A)
      coupling_strength[module_A + ' -> ' + module_B] = 0
      for dependencies_in_B in dependency_map.\
            get_files_creating_dependency_between(module_A, module_B).values():
        coupling_strength[module_A + ' -> ' + module_B] += \
          len(dependencies_in_B)

      logging.verbose(" -> (%d) %s "
                      % (coupling_strength[module_A + ' -> ' + module_B],
                         module_B),
                      end='')
      # Save away (for visualisation) the coupling strength found in the
      # current iteration.
      coupling_strength_collected.append(
        (module_A, module_B,
         coupling_strength[module_A + ' -> ' + module_B]))

    logging.verbose('')  # Line feed after the arrows joined above.
    maximal_coupling_edge = max(coupling_strength.items(),
                                key=itemgetter(1))[0]. \
      split(' -> ')
    to_merge, merge_into = maximal_coupling_edge[0], maximal_coupling_edge[1]

    # If a A<-B and B<-A merge is prepared (e.g. because an A->B->A and
    # B->A->B cycle exists), then moving files from B to A and then A to B
    # would just make the algorithm oscillate between two states.
    left_module_in_rights_list = to_merge in modules_to_merge.get(merge_into,
                                                                  list())
    right_module_in_lefts_list = merge_into in modules_to_merge.get(to_merge,
                                                                    list())
    if left_module_in_rights_list or right_module_in_lefts_list:
      # The solution here is to create a module C which merges A and B
      # together.
      modules_moved_together = [to_merge, merge_into]
      dummy_name = 'intermediate_' + \
                   mapping.get_new_module_name(module_map,
                                               modules_moved_together)
      modules_to_merge[dummy_name] = modules_moved_together

      if left_module_in_rights_list:
        logging.verbose("    ??<< Previous merge selected: %s -> %s"
                        % (to_merge, merge_into))
        modules_to_merge[merge_into].remove(to_merge)
      if right_module_in_lefts_list:
        logging.verbose("    ??<<   Previous merge selected: %s -> %s"
                        % (merge_into, to_merge))
        modules_to_merge[to_merge].remove(merge_into)
      modules_marked_for_moving.add(to_merge)
      modules_marked_for_moving.add(merge_into)

      logging.verbose("    ::!!   Creating new module: %s" % dummy_name)
      logging.verbose("    !! --> Merge decided: %s -> %s"
                      % (to_merge, dummy_name))
      logging.verbose("    !! --> Merge decided: %s -> %s"
                      % (merge_into, dummy_name))
      continue

    # Don't move a module twice in the same iteration.
    if to_merge in modules_marked_for_moving:
      logging.verbose("    !!     Skipping merge, %s is already marked for "
                      "another merge..." % to_merge)
      continue

    # Don't move a module into a module that's already being moved.
    if merge_into in modules_marked_for_moving:
      logging.verbose("    //     Derailing merge, target %s is "
                      "already marked for another merge..." % merge_into)
      # Find which module the originally selected target candidate will
      # merge into.
      for m, ms in modules_to_merge.items():
        if merge_into in ms:
          merge_into = m
          break
      logging.verbose("    \\\\     Target merges into %s"
                      % merge_into)

    merge_list = modules_to_merge.get(merge_into, list())
    if not merge_list:
      modules_to_merge[merge_into] = merge_list
    logging.verbose("    !! --> Merge decided: %s -> (%s) %s"
                    % (to_merge,
                       str(
                         coupling_strength.get(to_merge + ' -> ' + merge_into,
                                               "no direct coupling")),
                       merge_into))
    merge_list.append(to_merge)
    modules_marked_for_moving.add(to_merge)

  graph_visualisation('joins').draw_module_joins(
    modules_to_merge, coupling_strength_collected)
  graph_visualisation('joins').show()  # Blocking call!
  return modules_to_merge


def main(MODULE_MAP, DEPENDENCY_MAP):
  # Make sure the module-to-module import directives are in the dependency map,
  # as this stage operates based on them.
  DEPENDENCY_MAP.synthesize_intermodule_imports()

  iteration_count = 1
  while True:
    logging.essential(
      "========->> Begin iteration %d trying to merge cycles.. <<-========"
      % iteration_count)

    modules_to_move = _fold_cycles(MODULE_MAP, DEPENDENCY_MAP)
    if modules_to_move is True:
      logging.normal("Nothing to do.")
      break
    else:
      # Alter the module map with the calculated moves, and try running the
      # iteration again.
      logging.verbose("Will merge the following modules to fix the cyclical "
                      "dependency:")
      file_moves = dict()
      for module, ms_to_merge_into in sorted(filter(lambda e: e[1],
                                                    modules_to_move.items())):
        logging.verbose("    Into '%s':" % module)
        for module_to_move in ms_to_merge_into:
          logging.verbose("        %s" % module_to_move)
          for file in MODULE_MAP.get_fragment_list(module_to_move):
            file_moves[file] = module

      mapping.apply_file_moves(MODULE_MAP, DEPENDENCY_MAP, file_moves)
      iteration_count += 1

  mapping.fix_module_names(MODULE_MAP, DEPENDENCY_MAP)

  logging.essential(
    "-------- Final count of files in each modules after joining --------")
  for module in sorted(MODULE_MAP):
    length = len(MODULE_MAP.get_fragment_list(module))
    if length:
      logging.essential("     Module %s: %d" % (module, length))

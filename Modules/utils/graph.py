from collections import deque
import operator

try:
  import networkx as nx
except ImportError as e:
  print("Error! A dependency of this tool could not be satisfied. Please "
        "install the following Python package via 'pip' either to the "
        "system, or preferably create a virtualenv.")
  raise


def is_cutting_edge(edge, partitioning):
  """
  Decide whether :param edge: is a cutting edges on a graph that is
  partitioned to the vertex sets :param partitioning:.
  """
  if len(partitioning) != 2:
    raise TypeError("Partition must be a list of two lists.")

  u, v = edge
  S, T = partitioning[0], partitioning[1]

  return (u in S and v in T) or (u in T and v in S)


def generate_cutting_edges(edge_collection, partitioning):
  """
  Yields a generator that filters the edges from :param edge_collection: that
  are the cutting edges on a graph that is partitioned to the vertex sets
  :param partitioning:.

  :param edge_collection: should be a collection of pairs.
  :param partitioning: should be a pair of vertex name collections.
  """
  if len(partitioning) != 2:
    raise TypeError("Partition must be a list of two lists.")

  S, T = partitioning[0], partitioning[1]
  for u, v in edge_collection:
    if (u in S and v in T) or (u in T and v in S):
      yield (u, v)


def __transitive_leveled_graph_iteration(direction_fun, node):
  """
  Helper function to transivitely iterated a graph from a starting :param node:
  using the :param direction: lambda on the graph that generates the new
  "level" of nodes.
  """

  visited_nodes = set()
  work_queue = deque([list(direction_fun(node))])

  while work_queue:
    level = work_queue.popleft()
    yielded = []

    for elem in level:
      # Ignore nodes that had been "visited" already to prevent duplication.
      if elem in visited_nodes:
        continue

      visited_nodes.add(elem)
      yielded.append(elem)
      parent_collection = list(direction_fun(elem))
      if parent_collection:
        work_queue.append(parent_collection)

    yield yielded


def transitive_leveled_predecessors(graph, node):
  """
  Transitively generate the predecessors, grouped by level - distance from the
  node - of the given :param graph: starting from :param node:.
  The :param node: itself is not generated.
  """
  return __transitive_leveled_graph_iteration(graph.predecessors, node)


def transitive_leveled_successors(graph, node):
  """
  Transitively generate the successors, grouped by level - distance from the
  node - of the given :param graph: starting from :param node:.
  The :param node: itself is not generated.
  """
  return __transitive_leveled_graph_iteration(graph.successors, node)


def simple_cycles(directed_edges):
  """
  Generate shortest simple cycles using a quadratic algorithm.
  Useful when :func:`nx.simple_cycles()` does not terminate in a reasonable
  time.

  :return: (minimum_length, cycles), where `cycles` is a
  `dict(Node, [Nodes...])`, for each node listing one shortest path starting
  from that node. The path is represented as a list of nodes, which always
  contains the starting node as its prefix and suffix.
  """
  graph = nx.DiGraph(directed_edges)
  sorted_edges = sorted(directed_edges)

  # Generating the simple_cycles() of the dependency graph is very very costly
  # at this point, as for ~60 modules they could be the order of or above
  # 10 billion. Instead, this quadratic algorithm of the adjacency matrix will
  # try selecting shortest cycles.
  dependency_paths = dict()
  for n in sorted_edges:
    for m in sorted_edges:
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
    # If there are no cycles, quit.
    return 0, list()

  cycle_lengths = sorted(
    map(lambda e: (e[0], len(e[1])), dependency_paths.items()),
    key=operator.itemgetter(1))
  cycle_lengths_minimum = min(cycle_lengths, key=operator.itemgetter(1))[1]
  minimum_long_cycles = sorted(filter(
    lambda e: len(e[1]) == cycle_lengths_minimum,
    dependency_paths.items()))

  return cycle_lengths_minimum, minimum_long_cycles

from collections import deque


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

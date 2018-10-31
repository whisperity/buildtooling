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

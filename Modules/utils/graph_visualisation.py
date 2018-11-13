
try:
  import networkx as nx
  import matplotlib.pyplot as plt
except ImportError as e:
  print("Error! A dependency of this tool could not be satisfied. Please "
        "install the following Python package via 'pip' either to the "
        "system, or preferably create a virtualenv.")
  raise

from .graph import is_cutting_edge


COLOURS = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4',
           '#46f0f0', '#f032e6', '#bcf60c', '#fabebe', '#008080', '#e6beff',
           '#9a6324', '#fffac8', '#800000', '#aaffc3', '#808000', '#ffd8b1',
           '#000075', '#808080']


def draw_dependency_graph(cycle_graph, module_to_files_map):
  """
  Helper function that creates a visualisation of the graph
  :param cycle_graph:, which directed graph contains a file dependency
  hierarchy.

  :param module_to_files_map: A map that assigns a list of files belonging to
  a particular module.
  """
  pos = nx.nx_pydot.graphviz_layout(cycle_graph)
  for idx, item in enumerate(module_to_files_map.items()):
    module, files = item
    nx.draw_networkx_nodes(cycle_graph, pos,
                           nodelist=files,
                           node_color=COLOURS[idx])
    nx.draw_networkx_edges(cycle_graph, pos,
                           edgelist=cycle_graph.out_edges(files),
                           edge_color=COLOURS[idx])

  nx.draw_networkx_labels(cycle_graph, pos)
  plt.axis('off')


def draw_flow_and_cut(flow, cycle_graph, module_to_files_map,
                      cycle_start, cut_partition):
  """
  Helper function to visualise the flow graph :param flow: and mark the cut
  created by :param partition:.

  :param cycle_graph: The original file dependency graph from which the flow
  was created.
  :param module_to_files_map: A map that assigns a list of files belonging to
  a particular module.
  :param cycle_start: The name of the module in the map's keys where the
  cycle is "broken". This module will be expected to have a source and a sink
  node.
  :param cut_partition: The partition of nodes that results after cutting the
  flow graph.
  """
  pos = nx.nx_pydot.graphviz_layout(flow)
  capacities = dict(map(lambda e: ((e[0], e[1]), e[2]),
                        flow.edges(data='capacity')))

  def _draw_edge_from_names(name_collection, edge_endpoint_lambda,
                            colour_lambda, draw_capacity=False):
    """
    Helper function that draws all edges created by applying
    :param edge_endpoint_lambda: on the names in :param name_collection:.
    The created edge will be draw only if it is part of the :var flow: graph.

    :param colour_lambda: A lambda that is called with the generated edge
    tuple and decides what colour the edge will be drawn as.
    :param draw_capacity: If set to True, the the capacity of the edge
    will also be rendered.
    """
    for name in name_collection:
      edge = edge_endpoint_lambda(name)
      if edge in flow.edges:
        colour = colour_lambda(edge)
        nx.draw_networkx_edges(flow, pos,
                               edgelist=[edge],
                               edge_color=colour)

        if draw_capacity:
          capacity = capacities.get(edge, None)
          if capacity is not None and capacity != float('inf'):
            nx.draw_networkx_edge_labels(flow, pos,
                                         edge_labels={edge: capacity})

  module_to_colour = {}
  for i, module in enumerate(sorted(module_to_files_map.keys())):
    module_to_colour[module] = COLOURS[i]

    # Draw the nodes of the module.
    module_node_colour = 'black' if module != cycle_start else 'blue'

    module_node_list = ['-> ' + module + ' ->'] if module != cycle_start \
      else [module + ' ->', '-> ' + module]
    module_node_dict = dict(map(lambda e: (e, e), module_node_list))

    if all([module in flow.nodes for module in module_node_list]):
      nx.draw_networkx_nodes(flow, pos,
                             nodelist=module_node_list,
                             node_color=COLOURS[i],
                             node_shape='s')

      nx.draw_networkx_labels(flow, pos,
                              labels=module_node_dict,
                              font_color=module_node_colour)

    # Draw the file nodes belonging to the iterated module.
    dependees = list(filter(lambda e: e in flow.nodes,
                            map(lambda s: s + ' ->',
                                module_to_files_map[module])))
    dependencies = list(filter(lambda e: e in flow.nodes,
                               map(lambda s: '-> ' + s,
                                   module_to_files_map[module])))

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

    # ... and link them to the module node ...
    def dep_and_file_colour(edge):
      return '#ffa500' if is_cutting_edge(edge, cut_partition) else '#dddddd'

    _draw_edge_from_names(dependees,
                          lambda dependee: (module + ' ->', dependee),
                          dep_and_file_colour, True)
    _draw_edge_from_names(dependees,
                          lambda dependee: ('-> ' + module + ' ->', dependee),
                          dep_and_file_colour, True)

    _draw_edge_from_names(dependencies,
                          lambda dependency: (dependency, '-> ' + module),
                          dep_and_file_colour, True)
    _draw_edge_from_names(dependencies,
                          lambda dependency: (dependency,
                                              '-> ' + module + ' ->'),
                          dep_and_file_colour, True)

    # ... and for files that appear on both sides of a module, link them
    # to each other too.
    _draw_edge_from_names(module_to_files_map[module],
                          lambda file_in_module: ('-> ' + file_in_module,
                                                  file_in_module + ' ->'),
                          lambda edge: '#ffa500' if
                              is_cutting_edge(edge, cut_partition)
                            else '#666666')

  # Draw in the dependencies between distinct files from the original
  # dependency graph.
  for dependency_edge in cycle_graph.edges:
    edge = (dependency_edge[0] + ' ->', '-> ' + dependency_edge[1])
    if edge not in flow.edges:
      continue

    # Show the cut's edges in a different style. A cutting edge is an
    # edge which ends are in different partitions.
    if is_cutting_edge(edge, cut_partition):
      colour = '#ffa500'
      width = 4.0
      style = 'dashdot'
    else:
      from_filename = edge[0].replace(' ->', '').replace('-> ', '')
      from_modules = list(
        dict(filter(lambda m: from_filename in m[1],
                    module_to_files_map.items())).keys())
      colour = module_to_colour[from_modules[0]]
      width = 1.0
      style = 'solid'

      capacity = capacities.get(edge, None)
      if capacity is None or capacity == float('inf'):
        nx.draw_networkx_edge_labels(flow, pos,
                                     font_size=18,
                                     edge_labels={edge: '\u221E'})  # Inf sym.
        width = 0.333
      elif capacity == 0:
        nx.draw_networkx_edge_labels(flow, pos,
                                     font_size=18,
                                     edge_labels={edge: '\u2205'})  # Emptyset.
        width = 0.333

    nx.draw_networkx_edges(flow, pos,
                           edgelist=[edge],
                           width=width,
                           edge_color=colour,
                           style=style)
    # nx.draw_networkx_edge_labels(flow, pos,
    #                              font_size=10,
    #                              edge_labels=capacities)

  plt.axis('off')

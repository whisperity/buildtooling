
try:
  import networkx as nx
  import matplotlib.pyplot as plt
except ImportError as e:
  print("Error! A dependency of this tool could not be satisfied. Please "
        "install the following Python package via 'pip' either to the "
        "system, or preferably create a virtualenv.")
  raise


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

  module_to_colour = {}
  for i, module in enumerate(sorted(module_to_files_map.keys())):
    module_to_colour[module] = COLOURS[i]

    # Draw the nodes of the module.
    module_node_colour = 'black' if module != cycle_start else 'blue'

    module_node_list = ['-> ' + module + ' ->'] if module != cycle_start \
      else [module + ' ->', '-> ' + module]
    module_node_dict = dict(map(lambda e: (e, e), module_node_list))

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
    for dep in dependees:
      edge_try = (module + ' ->', dep)
      if edge_try in flow.edges:
        nx.draw_networkx_edges(flow, pos,
                               edgelist=[edge_try],
                               edge_color='#dddddd')
      else:
        edge_try = ('-> ' + module + ' ->', dep)
        if edge_try in flow.edges:
          nx.draw_networkx_edges(flow, pos,
                                 edgelist=[edge_try],
                                 edge_color='#dddddd')

    for dep in dependencies:
      edge_try = (dep, '-> ' + module)
      if edge_try in flow.edges:
        nx.draw_networkx_edges(flow, pos,
                               edgelist=[edge_try],
                               edge_color='#dddddd')
      else:
        edge_try = (dep, '-> ' + module + ' ->')
        if edge_try in flow.edges:
          nx.draw_networkx_edges(flow, pos,
                                 edgelist=[edge_try],
                                 edge_color='#dddddd')

    # ... and for files that appear on both sides of a module, link them
    # to each other too.
    for file_in_module in module_to_files_map[module]:
      self_edge = ('-> ' + file_in_module, file_in_module + ' ->')
      if self_edge in flow.edges:
        nx.draw_networkx_edges(flow, pos,
                               edgelist=[self_edge],
                               edge_color='#666666')

  # Draw in the file dependencies.
  for dependency_edge in cycle_graph.edges:
    u, v = dependency_edge[0] + ' ->', '-> ' + dependency_edge[1]
    # Show the cut's edges in a different style. A cutting edge is an
    # edge which ends are in different partitions.
    S, T = cut_partition[0], cut_partition[1]
    if (u in S and v in T) or (u in T and v in S):
      # colour = '#b33a3a'
      colour = '#ffa500'
      width = 4.0
      style = 'dashdot'
    else:
      from_filename = u.replace(' ->', '').replace('-> ', '')
      from_modules = list(
        dict(filter(lambda m: from_filename in m[1],
                    module_to_files_map.items())).keys())
      colour = module_to_colour[from_modules[0]]
      width = 1.0
      style = 'solid'

    nx.draw_networkx_edges(flow, pos,
                           edgelist=[(u, v)],
                           width=width,
                           edge_color=colour,
                           style=style)

  plt.axis('off')

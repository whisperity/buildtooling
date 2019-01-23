import sys

from ModulesTSMaker import mapping
from utils import logging
from utils.progress_bar import tqdm


DESCRIPTION = "Write Modules TS declaration (CPPM) files"


def main(START_FOLDER,
         MODULE_MAP,
         DEPENDENCY_MAP,
         HEADER_FILE_REGEX,
         EXTERNAL_INCLUDE_GRAPH):
  # Make sure the module-to-module import directives are in the dependency map,
  # as this stage operates based on them.
  DEPENDENCY_MAP.synthesize_intermodule_imports()

  # After the modules has been split up, commit the changes to the file system
  # for the upcoming operations.
  mapping.write_module_mapping(START_FOLDER, MODULE_MAP)

  # Files can transitively and with the employment of header guards,
  # recursively include each other, which is not a problem in normal C++,
  # but for imports this must be evaded, as the files are put into a module
  # wrapper, which should not include itself.
  # However, for this module "wrapper" file to work, the includes of the
  # module "fragments" (which are rewritten by this script) must be in
  # a good order.
  topological_success = True
  for module in tqdm(sorted(MODULE_MAP),
                     desc="Sorting files",
                     unit='module'):
    files_in_module = MODULE_MAP.get_fragment_list(module)
    headers_in_module = filter(HEADER_FILE_REGEX.search, files_in_module)

    # By default, put every file known to be mapped into the module into
    # the list. (But they are not marked to have any dependencies.)
    intramodule_dependencies = dict(map(lambda x: (x, []),
                                        headers_in_module))
    # Then add the list of known dependencies from the previous built map.
    for dependee_file, dep_pair in \
          filter(lambda e: HEADER_FILE_REGEX.search(e[0]),
                 DEPENDENCY_MAP.get_intramodule_dependencies(module).items()):
      dep_list = list()
      for tupl in dep_pair:
        # Remove the "kind" attribute from the dependency graph for this.
        filename, kind = tupl
        if kind == 'uses' and HEADER_FILE_REGEX.search(filename):
          dep_list.append(filename)
      if dep_list:
        # Only save the dependency into this dict if the file partook in any
        # uses-dependency relation.
        intramodule_dependencies[dependee_file] = dep_list

    module_success = mapping.write_topological_order(
      MODULE_MAP.get_filename(module),
      HEADER_FILE_REGEX,
      EXTERNAL_INCLUDE_GRAPH,
      intramodule_dependencies)
    topological_success = topological_success and module_success

  if not topological_success:
    logging.essential("Error: one of more module files' interface (header) "
                      "part could not have been sorted properly.",
                      file=sys.stderr)
    sys.exit(1)

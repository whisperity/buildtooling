import sys

from ModulesTSMaker import mapping


DESCRIPTION = "Load module mapping"


def main(START_FOLDER):
  # Get the current pre-existing module mapping for the project.
  module_map, duplicates = mapping.get_module_mapping(START_FOLDER)
  dependency_map = mapping.DependencyMap(module_map)

  if duplicates:
    print("Error: Some files are included into multiple modules. These files "
          "had been removed from the mapping!", file=sys.stderr)
    print('\n'.join(duplicates), file=sys.stderr)

  return module_map, dependency_map

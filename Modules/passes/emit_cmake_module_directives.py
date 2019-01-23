import os
import sys

import utils


DESCRIPTION = "Emit CMake set_module directives for build"


def main(MODULE_MAP, MODULES_CMAKE_SCRIPT):
  try:
    with open(MODULES_CMAKE_SCRIPT, 'w') as out:
      # Deploy the 'Modules.cmake' helper script to the project. It is expected
      # from the project to contain the necessary binding for this script's
      # usage and the ModulesList.cmake file in appropriate, project-specific
      # locations.
      with open(os.path.join(os.path.dirname(__file__), '..', 'Modules.cmake'),
                'r') as inp:
        out.write(inp.read())
  except Exception as e:
    utils.logging.essential("Error: Couldn't deploy 'Modules.cmake', because: "
                            "%s" % e,
                            file=sys.stderr)
    sys.exit(1)

  try:
    with open('ModuleList.cmake', 'w') as f:
      # Write the CMake set_module() directives to a file. These map CPPM files
      # created by the tool to compilations.
      for module in sorted(MODULE_MAP):
        f.write("set_module(%s %s)\n"
                % (module, MODULE_MAP.get_filename(module)))

      f.write("\n")

      # Emit the necessary dependencies (import module statements) between
      # modules into the build graph too.
      for module in sorted(MODULE_MAP):
        for dependency in sorted(
              MODULE_MAP.get_dependencies_of_module(module)):
          f.write("set_module_dependency(%s %s)\n"
                  % (module, dependency))
  except Exception as e:
    utils.logging.essential("Error: Couldn't write set_modules() directives, "
                            "because: %s " % e,
                            file=sys.stderr)
    sys.exit(1)

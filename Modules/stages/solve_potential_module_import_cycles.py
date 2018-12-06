import multiprocessing
import sys

from ModulesTSMaker import cycle_resolution, mapping


STAGE_NAME = "Solve potential module import cycles"


def main(MODULE_MAP, DEPENDENCY_MAP):
  # Make sure the module-to-module import directives are in the dependency map,
  # as this stage operates based on them.
  DEPENDENCY_MAP.synthesize_intermodule_imports()

  # Check if the read module map contains circular dependencies that make the
  # current module map infeasible, and try to resolve it.
  # It is to be noted that this algorithm is finite, as worst case the system
  # will fall apart to N distinct modules where N is the number of translation
  # units -- unfortunately there was no improvement on modularisation made in
  # this case...
  iteration_count = 1
  with multiprocessing.Pool() as pool:
    while True:
      print(
        "========->> Begin iteration %d trying to break cycles.. <<-========"
        % iteration_count)

      files_to_move = cycle_resolution.get_circular_dependency_resolution(
        pool, MODULE_MAP, DEPENDENCY_MAP)
      if files_to_move is False:
        print("Error! The modules contain circular dependencies on each other "
              "which cannot be resolved automatically by splitting them.",
              file=sys.stderr)
        sys.exit(1)
      elif files_to_move is True:
        # If the resolution of the cycles is to do nothing, there are no issues
        # with the mapping anymore.
        print("Nothing to do.")
        break
      else:
        # Alter the module map with the calculated moves, and try running the
        # iteration again.
        mapping.apply_file_moves(MODULE_MAP, DEPENDENCY_MAP, files_to_move)

      iteration_count += 1

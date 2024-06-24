import sys

from ModulesTSMaker import mapping
import utils
from utils.progress_bar import tqdm


DESCRIPTION = "Load \"implements\" relations from the analysed compilations"


def main(START_FOLDER, MODULE_MAP, DEPENDENCY_MAP):
  # The SYMBOL_ANALYSER_BINARY emits the knowledge about what file implements
  # symbols from what other file. This has to be added to the algorithm's
  # knowledge, as Module files (CPPMs) have to contain *both* interface and
  # implementation.
  header_implements_files = list(
    filter(lambda s: s.endswith("-implements.txt"),
           utils.walk_folder(START_FOLDER)))
  for directive_file in tqdm(header_implements_files,
                             desc="Finding implemented headers",
                             unit='file'):
    with open(directive_file, 'r') as directive_handle:
      for line in directive_handle:
        # Parse the output of the directive file. A line is formatted like:
        #     main.cpp##something.h
        try:
          parts = line.strip().split('##')
          implementee = utils.strip_folder(START_FOLDER, parts[0])
          implemented = utils.strip_folder(START_FOLDER, parts[1])
          DEPENDENCY_MAP.add_dependency(implementee, implemented, 'implements')
        except ValueError as ve:
          utils.logging.normal("Implements relation failed, because: %s"
                                % str(ve),
                                file=sys.stderr)
        except IndexError:
          utils.logging.essential("Invalid directive in file:\n\t%s" % line,
                                  file=sys.stderr)
          continue

  # The implements relations could make the whole setup insane when a
  # "header"'s contents is implemented by multiple translation units belonging
  # to different modules. Because the latter algorithm only *splits* modules
  # apart, if the initial mapping is insane, the calculations don't need to be
  # made, as further splits won't fix the input.
  insanity = mapping.get_dependency_map_implementation_insanity(DEPENDENCY_MAP)
  if insanity:
    utils.logging.essential("Error: The initial input of module-assignments "
                            "given to the algorithm is insane. At least one "
                            "interface (\"header\") file is implemented by "
                            "translation units assigned to multiple different "
                            "modules.", file=sys.stderr)

    for implemented, module_and_files in sorted(insanity.items()):
      module_of_implemented = next(
        MODULE_MAP.get_modules_for_fragment(implemented),
        None)
      utils.logging.normal(
        "Symbols of file '%s' in module '%s' (%s) is implemented by:"
        % (implemented,
           module_of_implemented,
           MODULE_MAP.get_filename(module_of_implemented)),
        file=sys.stderr)
      for module, file_list in sorted(module_and_files.items()):
        utils.logging.normal("    in module '%s' (%s):"
                             % (module, MODULE_MAP.get_filename(module)),
                             file=sys.stderr)
        for file in sorted(file_list):
          utils.logging.normal("        %s" % file, file=sys.stderr)

    utils.logging.essential(
      "Please review and change your code, or remove the problematic "
      "interface files from the assignment, reducing them to pure headers.",
      file=sys.stderr)
    sys.exit(1)

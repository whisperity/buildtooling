from ModulesTSMaker import mapping
from utils.progress_bar import tqdm


PASS_NAME = "Move implementation files to new modules"


def main(MODULE_MAP, DEPENDENCY_MAP, HEADER_FILE_REGEX):
  # Headers have been moved at this point, but only the module map in memory
  # has changed, not the original source code. The next step is to move the
  # non-header files alongside with the headers, for the types they implement
  # (as modules need to contain interface and implementation in the same "TU").
  implementation_files_to_move = dict()
  for module in tqdm(sorted(MODULE_MAP),
                     desc="Organising implementation files",
                     unit='module'):
    files_in_module = MODULE_MAP.get_fragment_list(module)

    for header in filter(HEADER_FILE_REGEX.search, files_in_module):
      dependee_set = DEPENDENCY_MAP.get_dependees(header)
      for dependee, kind in dependee_set:
        if kind != 'implements':
          continue

        modules_of_dependee = list(
          MODULE_MAP.get_modules_for_fragment(dependee))
        if modules_of_dependee[0] != module:
          implementation_files_to_move[dependee] = module

  mapping.apply_file_moves(MODULE_MAP,
                           DEPENDENCY_MAP,
                           implementation_files_to_move)

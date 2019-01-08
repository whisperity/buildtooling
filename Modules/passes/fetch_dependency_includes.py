import codecs
import sys

from ModulesTSMaker import include
import utils
from utils.progress_bar import tqdm

PASS_NAME = "Fetch dependency \"#include\"s from files"


def main(MODULE_MAP,
         DEPENDENCY_MAP,
         FILTER_FILE_REGEX,
         REMOVE_LINES_FROM_FILES):
  # Handle removing #include directives from files matching the given RegEx and
  # adding them as module imports instead.
  files = list(filter(FILTER_FILE_REGEX.search,
                      MODULE_MAP.get_all_fragments()))
  for file in tqdm(files,
                   desc="Collecting includes",
                   unit='file',
                   position=1):
    try:
      with codecs.open(file, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    except OSError as e:
      tqdm.write("Couldn't read file '%s': %s" % (file, e),
                 file=sys.stderr)
      continue

    lines_to_remove_from_file = include.filter_imports_from_includes(
      file, content, MODULE_MAP, DEPENDENCY_MAP)

    if not lines_to_remove_from_file:
      continue

    utils.append_to_dict_element(REMOVE_LINES_FROM_FILES,
                                 file,
                                 lines_to_remove_from_file)

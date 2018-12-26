import codecs
import sys

from ModulesTSMaker import include
from utils.progress_bar import tqdm

PASS_NAME = "Fetch dependency \"#include\"s from files"


def main(MODULE_MAP, DEPENDENCY_MAP, FILTER_FILE_REGEX):
  # Handle removing #include directives from files matching the given RegEx and
  # adding them as module imports instead.
  headers = list(filter(FILTER_FILE_REGEX.search,
                        MODULE_MAP.get_all_fragments()))
  for file in tqdm(headers,
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

    new_text = include.filter_imports_from_includes(
      file, content, MODULE_MAP, DEPENDENCY_MAP)

    if not new_text:
      # If no includes had been removed from the file, there is no change to do
      # and thus new_text is None.
      continue

    try:
      with codecs.open(file, 'w', encoding='utf-8', errors='replace') as f:
        f.write(new_text)
    except OSError as e:
      tqdm.write("Couldn't write file '%s': %s" % (file, e),
                 file=sys.stderr)
      continue

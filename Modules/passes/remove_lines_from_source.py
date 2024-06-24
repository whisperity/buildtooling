import codecs
import sys
from operator import itemgetter

from utils import logging
from utils.progress_bar import tqdm

DESCRIPTION = "Remove unnecessary lines from source files"


def main(REMOVE_LINES_FROM_FILES, NON_TOPOLOGICAL_FILES):
  for file, remove_list in tqdm(sorted(REMOVE_LINES_FROM_FILES.items()),
                                desc="Removing obsolete source text",
                                unit='file'):
    if file in NON_TOPOLOGICAL_FILES:
        logging.normal("%s: File marked as non-topological, not touching..."
                       % (file),
                       file=sys.stderr)
        continue

    try:
      with codecs.open(file, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    except OSError as e:
      logging.essential("Couldn't read file '%s': %s" % (file, e),
                        file=sys.stderr)
      continue

    lines = content.splitlines(True)
    linenos_to_remove = set(map(itemgetter(0), remove_list))
    try:
      with codecs.open(file, 'w', encoding='utf-8', errors='replace') as f:
        for i, line in enumerate(lines):
          if i in linenos_to_remove:
            continue
          f.write(line)
    except OSError as e:
      logging.essential("Couldn't write file '%s': %s" % (file, e),
                        file=sys.stderr)
      continue

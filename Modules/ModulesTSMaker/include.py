import os
import sys

from utils import partition
from utils.progress_bar import tqdm


def directive_to_filename(line):
  if not line.startswith('#include'):
    return None

  return line \
    .replace('#include', '') \
    .strip() \
    .lstrip(r'"<') \
    .rstrip(r'">')


def filename_to_directive(filename):
  # TODO: What if a file was included with <> instead of ""?
  return '#include "%s"' % filename


def filter_imports_from_includes(filename,
                                 text,
                                 modulemap,
                                 dependency_map):
  """
  Using the given :param modulemap:, filter the :param text: into a source
  code which does not contain '#include' statements to files that are mapped
  to any module. (Includes that are not mapped to any module remain.)

  :param dependency_map: The function's call builds the dependency map, which
  specifies that what files belonging to a module depend on what files
  belonging to other modules.

  :returns: The transformed source :param text: from which includes had been
  removed.
  """

  # Get the "first" module from the module map read earlier which contains
  # the included file as its own include (so the included file's code is
  # in the said module).
  # First is good enough as the module map is expected to had been uniqued out
  # earlier.
  def __get_module(include):
    return next(modulemap.get_modules_for_fragment(include), None)

  # Rearrange the include statements so all of them are on the top, and for
  # easier rewriting to "import", in alphabetical order.
  original_lines = text.splitlines(True)
  include_lines, other_lines = partition(
    lambda line: not line.startswith("#include"), original_lines)
  include_lines = list(sorted(include_lines))
  if not include_lines:
    # If the file contains no "#include" statements, no need to do anything.
    return

  lines_to_keep = []
  for line in tqdm(include_lines,
                   unit='directive',
                   desc=os.path.basename(filename),
                   position=0,
                   leave=False):
    included = directive_to_filename(line)
    if not included:
      continue

    module = __get_module(included)
    if not module:
      # If no module is found for the include, it might have been an include
      # from the local folder. Let's try that way first...
      original_included = included
      included = os.path.join(os.path.dirname(filename), included)
      module = __get_module(included)
      if not module:
        tqdm.write("%s: Include file '%s' not found in module mapping."
                   % (filename, original_included),
                   file=sys.stderr)
        lines_to_keep.append(line)
        continue

    dependency_map.add_dependency(filename, included, 'uses')

  def _keep_line(line):
    """
    Predicate to check if :param line: is to be kept in the file once the
    dependencies had been synthesised from it.
    """
    if line in other_lines:
      # Every line that is not an include line is kept.
      return True
    if line in include_lines:
      # For lines that are include statements, only keep them if we marked them
      # for keeping earlier.
      return line in lines_to_keep

    # Lines we don't know nothing about should be kept too.
    return True

  final_lines = filter(_keep_line, original_lines)

  return ''.join(final_lines)

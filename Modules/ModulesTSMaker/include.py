import os
import sys
from itertools import filterfalse
from operator import itemgetter

from utils import logging, partition
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


def get_included_files(text):
  """
  Filters the given source text for include directives and returns the file
  names included (as the directives specify, the include paths are not
  searched).
  """
  # QUESTION: Maybe a better approach is needed, like 'clang-scan-deps'?
  return list(map(directive_to_filename,
                  filter(lambda l: l.startswith('#include '),
                         text.splitlines())))


def filter_imports_from_includes(filename,
                                 text,
                                 modulemap,
                                 dependency_map,
                                 include_paths):
  """
  Using the given :param modulemap:, filter the :param text: into a source
  code which does not contain '#include' statements to files that are mapped
  to any module. (Includes that are not mapped to any module remain.)

  :param dependency_map: The function's call builds the dependency map, which
  specifies that what files belonging to a module depend on what files
  belonging to other modules.

  :param include_paths: Additional include paths discovered from the project.

  :returns: The line numbers and line contents of lines that should be removed,
  and the list of include directives (and line numbers) that should be kept.
  """
  if not include_paths:
      include_paths = []

  # Get the "first" module from the module map read earlier which contains
  # the included file as its own include (so the included file's code is
  # in the said module).
  # First is good enough as the module map is expected to had been uniqued out
  # earlier.
  def __get_module(include):
    return next(modulemap.get_modules_for_fragment(include), None)

  # Rearrange the include statements so all of them are on the top, and for
  # easier rewriting to "import", in alphabetical order.
  original_lines = list(enumerate(text.splitlines(True)))
  include_lines, other_lines = partition(
    lambda line: not line[1].startswith("#include"), original_lines)
  include_lines = sorted(include_lines, key=itemgetter(1))
  if not include_lines:
    # If the file contains no "#include" statements, no need to do anything.
    return list(), list()

  lines_to_keep = []
  for i, line in tqdm(include_lines,
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
      try_include_dirs = [os.path.dirname(filename)] + include_paths
      for include_dir in try_include_dirs:
        included = os.path.join(include_dir, original_included)
        module = __get_module(included)
        if module:
          break

      if not module:
        logging.normal("%s: Include file '%s' not found in module mapping."
                       % (filename, original_included),
                       file=sys.stderr)
        lines_to_keep.append((i, line))
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

  return list(filterfalse(_keep_line, original_lines)), \
         lines_to_keep

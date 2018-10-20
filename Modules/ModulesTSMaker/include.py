import codecs
import os

from utils import partition
from utils.progress_bar import tqdm


def directive_to_filename(line):
  if not line.startswith('#include'):
    return None

  return line \
    .replace('#include ', '') \
    .strip() \
    .lstrip(r'"<') \
    .rstrip(r'">')


def filter_imports_from_includes(filename,
                                 text,
                                 modulemap,
                                 intra_dependency_map):
  """
  Using the given :param modulemap:, transform the :param text: into a source
  code which does not contain '#include' statements to files that are mapped
  to any module. (Includes that are not mapped to anything remain.)

  :param modulemap: The modulemap is extended with the list of modules the
  module should depend on after the includes are filtered.

  :param intra_dependency_map: The function's call builds the intra-module
  dependency map (which file within a module includes which other files in
  the same module) into this variable.
  """

  # Get the "first" module from the module map read earlier which contains
  # the included file as its own include (so the included file's code is
  # in the said module).
  # First is good enough as the module map is expected to had been uniqued out
  # earlier.
  def __get_module(include):
    return next(
      filter(
        lambda item: include in item[1]['fragments'],
        modulemap.items()),
      (None, None))[0]

  # Rearrange the include statements so all of them are on the top, and for
  # easier rewriting to "import", in alphabetical order.
  include_lines, other_lines = partition(
    lambda line: not line.startswith("#include"),
    text.splitlines(True))
  include_lines = list(sorted(include_lines))

  self_module = __get_module(filename)

  if not include_lines:
    # If the file contains no "#include" statements, no need to do anything.
    return

  found_used_modules = set()
  lines_to_keep = []
  for line in tqdm(include_lines,
                   unit='directives',
                   desc=os.path.basename(filename),
                   position=0,
                   leave=False):
    import time
    time.sleep(0.01)
    included = directive_to_filename(line)
    if not included:
      continue

    module = __get_module(included)
    if not module:
      # If no module is found for the include, it might have been an include
      # from the local folder. Let's try that way first...
      included = os.path.join(os.path.dirname(filename), included)
      module = __get_module(included)
    if not module:
      # tqdm.write("%s: Included '%s' not found in module map"
      #            % (filename, included),
      #            file=sys.stderr)
      lines_to_keep.append(line.strip())
      continue

    if module == self_module and self_module is not None:
      # Files can transitively and with the employment of header guards,
      # recursively include each other, which is not a problem in normal C++,
      # but for imports this must be evaded, as the files are put into a module
      # wrapper, which should not include itself.
      # However, for this module "wrapper" file to work, the includes of the
      # module "fragments" (which are rewritten by this script) must be in
      # a good order.
      if self_module not in intra_dependency_map:
        intra_dependency_map[self_module] = {}
      if filename not in intra_dependency_map[self_module]:
        intra_dependency_map[self_module][filename] = set()
      intra_dependency_map[self_module][filename].add(included)
    else:
      found_used_modules.add(module)

  if found_used_modules:
    # Rewrite the file and eliminate the unneeded '#include' statements.
    with codecs.open(filename, 'w', encoding='utf-8', errors='replace') as f:
      if lines_to_keep:
        f.write("/* Lines kept because these files don't seem to belong to a "
                "module: */\n")
        f.write('\n'.join(lines_to_keep))
        f.write("\n\n")
      f.write(''.join(other_lines))

    # Append the found modules to the modulemapping as a module's module
    # dependency.
    if self_module:
      modulemap[self_module]['imported-modules'] |= found_used_modules
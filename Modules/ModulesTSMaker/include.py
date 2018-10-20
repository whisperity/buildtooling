import os
import sys
from utils import partition
from utils.progress_bar import tqdm
from . import util

def directive_to_filename(line):
  if not line.startswith('#include'):
    return None

  return line \
    .replace('#include ', '') \
    .strip() \
    .lstrip(r'"<') \
    .rstrip(r'">')


def handle_source_text(modulemap, self_dependency_map, file, text):
  """
  Handles mapping the #include statements to modules in a concatenated source
  text.
  """

  # Get the "first" module from the module map read earlier which contains
  # the included file as its own include (so the included file's code is
  # in the said module).
  # First is good enough as the module map was uniqued out earlier.
  def __get_module(include):
    return next(
      filter(
        lambda item: include in item[1],
        modulemap.items()),
      (None, None))[0]

  # Rearrange the include statements so all of them are on the top, and for
  # easier rewriting to "import", in alphabetical order.

  include_lines, other_lines = partition(
    lambda line: not line.startswith("#include"),
    text.splitlines(True))
  include_lines = list(sorted(include_lines))

  self_module = __get_module(file)

  if not include_lines:
    # If the file contains no "#include" statements, no need to do anything.
    return

  found_used_modules = set()
  lines_to_keep = []
  for line in tqdm(include_lines,
                   unit='directives',
                   desc=os.path.basename(file),
                   position=0,
                   leave=False):
    included = directive_to_filename(line)
    if not included:
      continue

    module = __get_module(included)
    if not module:
      # If no module is found for the include, it might have been an include
      # from the local folder. Let's try that way first...
      included = os.path.join(os.path.dirname(file), included)
      module = __get_module(included)
    if not module:
      tqdm.write("%s: Included '%s' not found in module map"
                 % (file, included),
                 file=sys.stderr)
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
      if self_module not in self_dependency_map:
        self_dependency_map[self_module] = {}
      if file not in self_dependency_map[self_module]:
        self_dependency_map[self_module][file] = set()
      self_dependency_map[self_module][file].add(included)
    else:
      found_used_modules.add(module)

  new_includes = "/* Automatically generated include list. */\n" + \
                 '\n'.join(lines_to_keep) + \
                 "\n\n" + \
                 '\n'.join(["import MODULE_NAME_" + mod + ';'
                            for mod in found_used_modules])

  with open(os.devnull, 'w') as f:
    f.write(new_includes)
    f.write("\n\n")
    f.write('\n'.join(other_lines))
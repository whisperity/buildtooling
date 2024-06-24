import codecs
import os
import subprocess
import sys
from itertools import filterfalse, tee

from . import logging

__all__ = ['graph',
           'graph_visualisation',
           'logging',
           'progress_bar']


def partition(pred, iterable):
  """Partition an iterable to entries that pass or not pass a predicate."""
  it1, it2 = tee(iterable)
  return filterfalse(pred, it1), filter(pred, it2)


def strip_folder(folder, path):
  return os.path.abspath(path) \
         .replace(os.path.abspath(folder), '') \
         .lstrip('/')


def walk_folder(folder):
  for dirp, _, files in os.walk(folder):
    for file in files:
      yield strip_folder(folder, os.path.join(dirp, file))


def call_process(command, args=None, **kwargs):
  """
  Calls the given process with the optional arguments. Returns True and the
  output of the called binary if the call succeeded, or False and the error
  reason if it haven't.

  Additional arguments in :param kwargs: are passed to :fun subprocess.run():.
  """
  if not args:
    args = []
  if 'stdout' not in kwargs:
    kwargs['stdout'] = subprocess.PIPE
  if 'stderr' not in kwargs:
    kwargs['stderr'] = subprocess.STDOUT

  try:
    p = subprocess.run([command] + args,
                       check=True,
                       **kwargs)
    return True, '', p.stdout.decode('utf-8') if p.stdout else ''
  except subprocess.CalledProcessError as e:
    print("Error! The call did not succeed, because\n%s" % str(e),
          file=sys.stderr)
    return False, str(e), e.stdout.decode('utf-8') if e.stdout else ''
  except OSError as e:
    print("Error! The call did not succeed, because a system error:\n%s"
          % str(e),
          file=sys.stderr)
    return False, str(e), ''


def replace_at_position(filename, line, col, from_str, to_str):
  """
  Replace the string starting in file :param filename: at line :param line: at
  the character :param col: from :param from_str: to :param to_str:.

  :param line: and :param col: are 1-based indices, not 0-based!

  :return: True if the replacement took place, False otherwise.
  """
  try:
    with codecs.open(filename, 'r+',
                     encoding='utf-8', errors='replace') as handle:
      lines = list(handle)
      if len(lines) < line:
        raise IndexError("The file does not contain a line with number %d"
                         % line)
      line_to_change = lines[line - 1]
      if len(line_to_change) < col:
        raise IndexError("The line %d at column %d is already over."
                         % (line, col))

      line_tail = line_to_change[col - 1:]
      if not line_tail.startswith(from_str):
        raise KeyError("The replacement at the given position did not match "
                       "the given string that were to be replaced.")

      new_tail = line_tail.replace(from_str, to_str, 1)
      new_line = line_to_change[:col - 1] + new_tail
      lines[line - 1] = new_line

      handle.seek(0)
      handle.truncate(0)
      handle.write(''.join(lines))

      return True
  except Exception as e:
    logging.verbose("Couldn't do replacement in '%s' (%d:%d) '%s' -> '%s' "
                    "because %s: %s"
                    % (filename, line, col, from_str, to_str,
                       str(type(e)), str(e)),
                    file=sys.stderr)
    return False


def append_to_dict_element(Dict, key, value,
                           default_value=None,
                           append_method=list.__iadd__):
  """
  Appends the value to the key element of the dict. In case the dict does not
  contain the given element, a default value is constructed. The append is done
  with the given appender function.

  This method is useful for falsy-capable containers.
  """
  if default_value is None:
    default_value = list()

  stored_element = Dict.get(key, default_value)
  if not stored_element:
    # An empty container was retrieved
    Dict[key] = stored_element

  append_method(stored_element, value)

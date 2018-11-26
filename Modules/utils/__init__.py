import os
import subprocess
import sys
from itertools import filterfalse, tee

__all__ = ['progress_bar', 'graph_visualisation']


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
    return True, '', p.stdout.decode('utf-8')
  except subprocess.CalledProcessError as e:
    print("Error! The call did not succeed, because\n%s" % str(e),
          file=sys.stderr)
    return False, str(e), e.stdout.decode('utf-8')
  except OSError as e:
    print("Error! The call did not succeed, because a system error:\n%s"
          % str(e),
          file=sys.stderr)
    return False, str(e), ''

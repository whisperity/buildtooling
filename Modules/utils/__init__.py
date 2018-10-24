import os
from itertools import filterfalse, tee

__all__ = ['progress_bar']


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

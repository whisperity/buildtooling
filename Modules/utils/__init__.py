import os
from collections import Counter
from itertools import filterfalse, tee

__all__ = ['progress_bar']


def eliminate_dict_listvalue_duplicates(d):
  """
  Eliminates the duplicate values in a dict's value side.

  :returns: The eliminated dict, and the list of duplicate values.
  """
  counts = Counter(sum(d.values(), []))
  for key, value in d.items():
    d[key] = list(filter(lambda x: counts[x] == 1, value))

  return d, \
    list(
      dict(
        filter(lambda it: it[1] != 1,
               counts.items()))
      .keys())


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
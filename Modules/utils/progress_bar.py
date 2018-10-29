import sys

try:
  from tqdm import tqdm
except ImportError:
  class tqdm():
    """
    tqdm progress bar wrapper if the 'tqdm' package is not installed.
    """

    def __init__(self, iterable, *i, **kwargs):
      self.iterable = iterable
      self.total = kwargs.get('total', None)

    def __enter__(self):
      return self

    def __exit__(self, *exc):
      return False

    def __del__(self):
      pass

    def __iter__(self):
      for e in self.iterable:
        yield e

    def __len__(self):
      return self.total if self.iterable is None else \
        (self.iterable.shape[0] if hasattr(self.iterable, "shape")
         else len(self.iterable) if hasattr(self.iterable, "__len__")
         else getattr(self, "total", None))

    @staticmethod
    def write(*args, **kwargs):
      return print(*args, **kwargs)

  print("Python library 'tqdm' not found, no progress will be printed.",
        file=sys.stderr)

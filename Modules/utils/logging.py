import copy

from .progress_bar import tqdm

_LOGGING_CONFIGURATION = {
  'essential': True,
  'normal': True,
  'verbose': False}

__all__ = ['essential',
           'normal',
           'verbose']


def set_configuration(key, value):
  _LOGGING_CONFIGURATION[key] = value


def get_configuration():
  return copy.deepcopy(_LOGGING_CONFIGURATION)


def _runner(verbosity, *args, **kwargs):
  if _LOGGING_CONFIGURATION.get(verbosity, True):
    # Using tqdm.write() here because if there isn't a progress bar visible,
    # it can nicely fall back to normal printing, so "tqdm context" does not
    # need to be managed.
    tqdm.write(*args, **kwargs)


def essential(*args, **kwargs):
  _runner('essential', *args, **kwargs)


def normal(*args, **kwargs):
  _runner('normal', *args, **kwargs)


def verbose(*args, **kwargs):
  _runner('verbose', *args, **kwargs)

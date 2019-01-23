import copy

_LOGGING_CONFIGURATION = dict()

__all__ = ['essential',
           'normal',
           'verbose']

def set_configuration(key, value):
  _LOGGING_CONFIGURATION[key] = value

def get_configuration():
  return copy.deepcopy(_LOGGING_CONFIGURATION)

def essential(*args, **kwargs):
  print("ESSENTIAL")
  # print(*args, **kwargs)

def normal(*args, **kwargs):
  print("NORMAL")

def verbose(*args, **kwargs):
  print("VERBOSE")
  # print(*args, **kwargs)
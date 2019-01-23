import importlib.util
import inspect
import os
import sys
import time

from utils import logging

PACKAGE_DIR = os.path.dirname(__file__)
__all__ = ['PassLoader']


class PassLoader():
  """
  Wrapper for passes of the project. Takes care of binding and bookkeeping
  configuration globals.
  """

  loaded_passes = dict()
  cfg_globals = dict()
  timing_informations = list()

  @classmethod
  def load_stage(cls, pass_name):
    file_name = pass_name + '.py'
    full_name = 'passes.' + pass_name
    module_path = os.path.join(PACKAGE_DIR, file_name)

    # Try loading the module dynamically.
    # (Thanks to https://stackoverflow.com/a/67692/1428773)
    spec = importlib.util.spec_from_file_location(full_name, module_path)
    loaded_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded_module)

    sys.modules[full_name] = loaded_module
    cls.loaded_passes[pass_name] = loaded_module

  @classmethod
  def register_global(cls, var, val):
    if val is None and var in cls.cfg_globals:
      del cls.cfg_globals[var]
      return

    cls.cfg_globals[var] = val

  @classmethod
  def get(cls, var):
    return cls.cfg_globals.get(var, None)

  @classmethod
  def execute_pass(cls, pass_name):
    """
    Executes the pass named :param pass_name:. This call will implicitly load
    the pass' module and the execution will get the "globals" registered to
    this class at the moment of calling execute_pass().
    """
    if pass_name not in cls.loaded_passes:
      cls.load_stage(pass_name)
      if pass_name not in cls.loaded_passes:
        raise KeyError("The stage '%s' was not found." % pass_name)

    pass_module = cls.loaded_passes[pass_name]
    logging.essential("\n!>>>>>>> Executing pass '%s' (%s)... <<<<<<<!"
                      % (pass_name, pass_module.DESCRIPTION))

    # Dynamically figure out what "global" variables (state) the stage needs
    # based on the signature and map it from the stored globals.
    fun = pass_module.main
    params = inspect.signature(fun).parameters
    globals_needed_by_params = dict(
      filter(lambda e: e[0] in params, cls.cfg_globals.items()))
    binding = inspect.signature(fun).bind(**globals_needed_by_params)
    binding.apply_defaults()

    started = time.time()
    returns = fun(*binding.args, **binding.kwargs)
    ended = time.time()

    cls.timing_informations.append((pass_name, started, ended))
    return returns

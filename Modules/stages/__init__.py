import importlib.util
import inspect
import os
import sys


PACKAGE_DIR = os.path.dirname(__file__)
__all__ = ['ExecutionStepWrapper']


class ExecutionStepWrapper():
  """
  Wrapper for execution steps of the project. Takes care of binding and
  bookkeeping configuration globals.
  """

  loaded_stages = {}
  cfg_globals = {}

  @classmethod
  def load_stage(cls, stage_name):
    file_name = stage_name + '.py'
    full_name = 'stages.' + stage_name
    module_path = os.path.join(PACKAGE_DIR, file_name)

    # Try loading the module dynamically.
    # (Thanks to https://stackoverflow.com/a/67692/1428773)
    spec = importlib.util.spec_from_file_location(full_name, module_path)
    loaded_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded_module)

    sys.modules[full_name] = loaded_module
    cls.loaded_stages[stage_name] = loaded_module

  @classmethod
  def register_global(cls, var, val):
    cls.cfg_globals[var] = val

  @classmethod
  def execute_stage(cls, stage_name):
    """
    Executes the stage named :param stage_name:. This call will implicity load
    the stage's module and the execution will get the "globals" registered to
    this class at the moment of calling execute_stage().
    """
    if stage_name not in cls.loaded_stages:
      cls.load_stage(stage_name)
      if stage_name not in cls.loaded_stages:
        raise KeyError("The stage '%s' was not found." % stage_name)

    # Dinamically figure out what "global" variables (state) the stage needs
    # based on the signature and map it from the stored globals.
    fun = cls.loaded_stages[stage_name].main
    params = inspect.signature(fun).parameters
    globals_needed_by_params = dict(
      filter(lambda e: e[0] in params, cls.cfg_globals.items()))
    binding = inspect.signature(fun).bind(**globals_needed_by_params)
    binding.apply_defaults()

    return fun(*binding.args, **binding.kwargs)

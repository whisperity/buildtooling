import importlib.util
import os

from .. import logging

__all__ = ['get_visualizer', 'load_for']

__SELECTED_EXECUTORS = dict()
__LOADED_IMPL_MODULES = dict()


def _create_module(name):
  # Try loading the module dynamically.
  # (Thanks to https://stackoverflow.com/a/67692/1428773)
  spec = importlib.util.spec_from_file_location(
    name + '.py',
    os.path.join(os.path.dirname(__file__), name + '.py'))
  loaded_module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(loaded_module)

  # Make the loaded module accessible.
  __LOADED_IMPL_MODULES[name] = loaded_module


def get_visualizer(action):
  """
  Gets the visualizer associated with the given action.
  """
  module = __SELECTED_EXECUTORS.get(action, None)
  if not module:
    raise ModuleNotFoundError("The visualizer library has not been load()ed "
                              "yet.")
  return module


def load_for(action, should_actually_execute=False):
  """
  Load the implementation module for graph visualisations. In case
  :var should_actually_execute: is False, a dummy library which does nothing
  when called. A separate module can be loaded based on the :var action: key.
  """
  module_name_to_load = 'actual' if should_actually_execute else 'dummy'
  if not __LOADED_IMPL_MODULES.get(module_name_to_load, None):
    # Load the needed implementation module, but only once per session!
    _create_module(module_name_to_load)

  # Set the loaded module into the user-accessible data structure.
  __SELECTED_EXECUTORS[action] = __LOADED_IMPL_MODULES[module_name_to_load]

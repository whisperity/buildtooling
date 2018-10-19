foreach(_moduleName IN LISTS REGISTERED_MODULES)
  # Remove information from every configured module if the build is
  # reconfigured.
  unset(Module_${_moduleName}_SOURCE CACHE)
endforeach()

set(REGISTERED_MODULES "" CACHE INTERNAL "Known C++ Modules-TS modules." FORCE)

# Save the knowledge that _moduleName is compiled from the given CPPM.
function(set_module _moduleName _moduleCPPM)
  get_filename_component(_moduleFile ${_moduleCPPM} ABSOLUTE)

  set(Module_${_moduleName}_SOURCE ${_moduleFile}
    CACHE INTERNAL "Module source file for ${_moduleName}" FORCE)
  list(APPEND REGISTERED_MODULES ${_moduleName})
  set(REGISTERED_MODULES ${REGISTERED_MODULES}
    CACHE INTERNAL "Known C++ Modules-TS modules." FORCE)
endfunction()

# Add the dependency of the module to the given target. This module is
# compiled with the options needed for the particular target, to prevent
# mismatches of reusing a module compiled initially for another target.
function(add_module_to_target _target _moduleName)
  string(MAKE_C_IDENTIFIER ${_target} _target_fix)
  set(_targetedModule "${_target_fix}_${_moduleName}")

  add_cxx_module(${_targetedModule} ${Module_${_moduleName}_SOURCE})
  target_compile_definitions(${_targetedModule}
    PRIVATE
    FULL_NAME_${_moduleName}=${_targetedModule})

  target_link_libraries(${_target} ${_targetedModule})
  target_compile_definitions(${_target}
    PRIVATE
    MODULE_NAME_${_moduleName}=${_targetedModule})
endfunction()

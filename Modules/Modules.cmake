# This is a helper CMake script that allows for usage of C++ Modules TS modules
# based on the CMake version found at
#     http://gitlab.kitware.com/whisperity/CMake.git on branch clang-modules
# You need this CMake, and a Modules-TS capable compiler (such as Clang >= 4.0).
set(CMAKE_MINIMUM_REQUIRED_VERSION 3.13.2)

foreach(_moduleName IN LISTS REGISTERED_MODULES)
  # Remove information from every configured module if the build is
  # reconfigured.
  unset(Module_${_moduleName}_SOURCE CACHE)
  unset(Module_${_moduleName}_DEPENDENCIES CACHE)
endforeach()

set(REGISTERED_MODULES "" CACHE INTERNAL "Known C++ Modules-TS modules." FORCE)

# Save the knowledge that _moduleName is compiled from the given CPPM.
function(set_module _moduleName _moduleCPPM)
  get_filename_component(_moduleFile ${_moduleCPPM} ABSOLUTE)

  set(Module_${_moduleName}_SOURCE ${_moduleFile}
    CACHE INTERNAL "Module source file for ${_moduleName}" FORCE)
  set(Module_${_moduleName}_DEPENDENCIES ""
      CACHE INTERNAL "Module-to-module dependencies for ${_moduleName}" FORCE)

  list(APPEND REGISTERED_MODULES ${_moduleName})
  set(REGISTERED_MODULES ${REGISTERED_MODULES}
    CACHE INTERNAL "Known C++ Modules-TS modules." FORCE)
endfunction()

# Save the knowledge that _moduleName module depends on (imports) the module
# _dependencyModuleName.
function(set_module_dependency _moduleName _dependencyModuleName)
  list(APPEND Module_${_moduleName}_DEPENDENCIES ${_dependencyModuleName})
  set(Module_${_moduleName}_DEPENDENCIES ${Module_${_moduleName}_DEPENDENCIES}
      CACHE INTERNAL "Module-to-module dependencies for ${_moduleName}" FORCE)
endfunction()

# Add the dependency of the module to the given target. This module is
# compiled with the options needed for the particular target, to prevent
# mismatches of reusing a module compiled initially for another target.
function(add_module_to_target _target _moduleName)
  string(MAKE_C_IDENTIFIER ${_target} _target_fix)

  # Create a C++ Modules TS module for the given target.
  set(_targetedModule "${_target_fix}_${_moduleName}")
  add_cxx_module(${_targetedModule} ${Module_${_moduleName}_SOURCE})
  target_compile_definitions(${_targetedModule}
    PRIVATE
    FULL_NAME_${_moduleName}=${_targetedModule})

  # Ensure the module gets built before and linked to the target.
  target_compile_definitions(${_target}
    PRIVATE
    MODULE_NAME_${_moduleName}=${_targetedModule})
  target_link_libraries(${_target} ${_targetedModule})

  # Handle module-to-module dependencies.
  foreach(_dependencyModule IN LISTS Module_${_moduleName}_DEPENDENCIES)
    set(_dependencyModuleFullName ${_target_fix}_${_dependencyModule})
    target_compile_definitions(${_targetedModule}
      PRIVATE
      MODULE_NAME_${_dependencyModule}=${_dependencyModuleFullName})
    target_link_libraries(${_targetedModule} ${_dependencyModuleFullName})
  endforeach()
endfunction()

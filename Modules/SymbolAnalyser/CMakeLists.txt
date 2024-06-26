cmake_minimum_required(VERSION 3.12)
project(SymbolAnalyser CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_FLAGS "-W -Wall -Wextra -pedantic \
  -std=c++17")

find_package(LLVM REQUIRED CONFIG)
message(STATUS "Found LLVM: ${LLVM_PACKAGE_VERSION}")
message(STATUS "            at ${LLVM_DIR}")
find_package(Clang REQUIRED CONFIG)
message(STATUS "Found Clang at ${Clang_DIR}")

include_directories(SYSTEM
    ${LLVM_INCLUDE_DIRS}
    ${CLANG_INCLUDE_DIRS})

# A Clang tool needs the Clang-specific standard headers in the
# "../lib/clang/<version>/include" folder so that tooling works.
add_custom_target(ClangHeaders
    ALL
    mkdir -p ../lib
    COMMAND rm -f ../lib/clang
    COMMAND ln -s ${LLVM_LIBRARY_DIRS}/clang ../lib/clang
    COMMENT "Making necessary Clang headers available...")

link_directories(${LLVM_LIBRARY_DIRS} ${CLANG_LIBRARY_DIRS})
set(CMAKE_BUILD_RPATH ${LLVM_LIBRARY_DIRS})
add_definitions(${LLVM_DEFINITIONS} ${CLANG_DEFINITIONS})

if(NOT ${LLVM_ENABLE_RTTI})
  # Need to disable RTTI in the client project in case dependency doesn't have
  # it either.
  message(STATUS "LLVM is without RTTI")
  add_compile_options(-fno-rtti)
else()
  message(STATUS "LLVM is with RTTI")
endif()

add_subdirectory(vendor)

set(LLVM_LIBRARIES_USED "")
list(APPEND LLVM_LIBRARIES_USED
    clang
    clangAST
    clangASTMatchers
    clangBasic
    clangFrontend
    clangSerialization
    clangTooling
    LLVMSupport)

add_library(RewritingTool STATIC
    Executor.cpp
    ImplementsEdges.cpp
    Replacement.cpp
    SymbolTableDump.cpp
    TheFinder.cpp)

add_executable(SymbolAnalyser
    main.cpp)
target_include_directories(SymbolAnalyser SYSTEM PUBLIC vendor)
target_link_libraries(SymbolAnalyser
    RewritingTool
    ${LLVM_LIBRARIES_USED}
    WhisperityHelper)

if (CMAKE_BUILD_TYPE STREQUAL "Debug")
    find_package(GTest)
    if (NOT ${GTEST_FOUND})
      message(WARNING "Debug build was enabled but GoogleTest library not"
                      "found.")
    else()
      enable_testing()

      include_directories(SYSTEM
          ${GTEST_INCLUDE_DIRS})
      include_directories(${CMAKE_CURRENT_SOURCE_DIR})
      add_executable(Test
          Test.cpp
          tests/DeclarationRewriting.cpp
          tests/ImplementsWriting.cpp
          tests/ImplementsRelation.cpp
          tests/MatchProblematicDeclarations.cpp
          tests/NontrivialIncludeFlags.cpp
          tests/RenameWriting.cpp
          tests/UsagePoints.cpp)
      target_link_libraries(Test
          ${GTEST_BOTH_LIBRARIES}
          RewritingTool
          ${LLVM_LIBRARIES_USED}
          pthread)

      add_test(
          NAME Test
          COMMAND Test)
      add_custom_target(check
          COMMAND ${CMAKE_CTEST_COMMAND}
          DEPENDS Test)
    endif()
endif()

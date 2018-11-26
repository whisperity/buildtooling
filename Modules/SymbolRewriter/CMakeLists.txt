cmake_minimum_required(VERSION 3.12)
project(SymbolRewriter CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_FLAGS "-W -Wall -Wextra -pedantic \
  -std=c++17")

find_package(LLVM REQUIRED CONFIG)
find_package(Clang REQUIRED CONFIG)

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
add_definitions(${LLVM_DEFINITIONS} ${CLANG_DEFINITIONS})
set(LLVM_LIBRARIES_USED "")
list(APPEND LLVM_LIBRARIES_USED
    clang
    clangAST
    clangASTMatchers
    clangBasic
    clangFrontend
    clangTooling
    LLVMSupport)

add_library(RewritingTool STATIC
    Executor.cpp
    Replacement.cpp
    TheFinder.cpp)

add_executable(SymbolRewriter
    main.cpp)
target_link_libraries(SymbolRewriter
    RewritingTool
    ${LLVM_LIBRARIES_USED}
    pthread)

if (CMAKE_BUILD_TYPE STREQUAL "Debug")
    enable_testing()
    find_package(GTest)

    include_directories(SYSTEM
        ${GTEST_INCLUDE_DIRS})
    include_directories(${CMAKE_CURRENT_SOURCE_DIR})
    add_executable(RewriteTest
        Test.cpp
        tests/DeclarationRewriting.cpp
        tests/MatchProblematicDeclarations.cpp
        tests/RenameWriting.cpp
        tests/UsagePoints.cpp)
    target_link_libraries(RewriteTest
        RewritingTool
        ${GTEST_BOTH_LIBRARIES}
        ${LLVM_LIBRARIES_USED}
        pthread)

    add_test(
        NAME RewriteTest
        COMMAND RewriteTest)
    add_custom_target(check
        COMMAND ${CMAKE_CTEST_COMMAND}
        DEPENDS RewriteTest)
endif()

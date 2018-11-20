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

add_executable(SymbolRewriter
    main.cpp
    TheFinder.cpp)
target_link_libraries(SymbolRewriter PRIVATE
    clang
    clangAST
    clangASTMatchers
    clangBasic
    clangFrontend
    clangTooling
    LLVMSupport)

cmake_minimum_required(VERSION 3.5.1)
project(Dummy)

include(cotire)

add_library(Implementation
  impl.cpp)
cotire(Implementation)

add_executable(Program
  main.cpp)
target_link_libraries(Program
  LINK_PUBLIC Implementation)
cotire(Program)

add_executable(Recursive
  template.cpp)
target_compile_options(Recursive PUBLIC
  -fpermissive)
cotire(Recursive)

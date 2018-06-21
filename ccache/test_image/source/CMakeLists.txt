cmake_minimum_required(VERSION 3.5.1)
project(Dummy)

add_library(Implementation
  impl.cpp)

add_executable(Program
  main.cpp)
target_link_libraries(Program
  LINK_PUBLIC Implementation)

add_executable(Recursive
  template.cpp)
target_compile_options(Recursive PUBLIC
  -fpermissive)

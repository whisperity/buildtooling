add_library(WhisperityHelper
  whisperity/ThreadsafeOStream.cpp)
target_link_libraries(WhisperityHelper PUBLIC
  pthread)


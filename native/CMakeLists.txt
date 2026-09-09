# Optional CMake build for the native tools. The Makefile next door does the same job;
# this exists for anyone whose toolchain expects CMake.
#
#   cmake -S native -B native/build -DCMAKE_BUILD_TYPE=Release
#   cmake --build native/build
#   ctest --test-dir native/build --output-on-failure

cmake_minimum_required(VERSION 3.16)
project(predly_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
endif()

if(MSVC)
  add_compile_options(/W4 /permissive- /D_USE_MATH_DEFINES)
else()
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

add_library(predly_odds INTERFACE)
target_include_directories(predly_odds INTERFACE ${CMAKE_CURRENT_SOURCE_DIR})

foreach(tool odds_cli vectors_test montecarlo backtest)
  add_executable(${tool} ${tool}.cpp)
  target_link_libraries(${tool} PRIVATE predly_odds)
endforeach()

set_target_properties(odds_cli PROPERTIES OUTPUT_NAME odds)

enable_testing()

add_test(NAME vectors
         COMMAND vectors_test ${CMAKE_CURRENT_SOURCE_DIR}/../verify/vectors.json)

add_test(NAME closed_form_matches_simulation
         COMMAND montecarlo 40000 --steps 600)

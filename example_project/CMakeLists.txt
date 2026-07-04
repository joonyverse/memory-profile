cmake_minimum_required(VERSION 3.10)
project(memory_profile_example)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Enable debug symbols for pahole
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -g")

include_directories(inc)

add_executable(memory_profile_example
    src/main.cpp
    src/example_node.cpp
    src/example_events.cpp
    src/example_system.cpp
    src/example_advanced.cpp
)

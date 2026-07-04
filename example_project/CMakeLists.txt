cmake_minimum_required(VERSION 3.10)
project(memory_profile_example)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Force Debug build type and enable debug symbols without optimizations
set(CMAKE_BUILD_TYPE Debug)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -g -O0")

include_directories(inc)

add_executable(memory_profile_example
    src/main.cpp
    src/example_node.cpp
    src/example_events.cpp
    src/example_system.cpp
    src/example_advanced.cpp
)

# GDB profiling configuration
set(CELL_SETUP_FUNC "complete_cell_setup" CACHE STRING "Name of the cell setup completion function to trace")
set(SCAN_SRC_DIR "${CMAKE_CURRENT_SOURCE_DIR}/inc" CACHE STRING "Directory to scan for structs/classes")

# Configure the GDB script template dynamically
configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/../tools/memory_analyzer/cell_trace.gdb.in"
    "${CMAKE_CURRENT_BINARY_DIR}/cell_trace.gdb"
    @ONLY
)

# Target for static DWARF structure layout parsing
add_custom_target(trace-static
    COMMAND "${CMAKE_CURRENT_SOURCE_DIR}/../tools/memory_analyzer/auto_scan.sh" "${SCAN_SRC_DIR}" "structs_list.txt"
    COMMAND gdb -batch -ex "source ${CMAKE_CURRENT_SOURCE_DIR}/../tools/memory_analyzer/analyze_struct.py" -ex "quit" ./memory_profile_example > struct_report.txt
    DEPENDS memory_profile_example
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    COMMENT "Generating static structures layout report..."
)

# Target for dynamic breakpoint cell setup heap mapping
add_custom_target(trace-dynamic
    COMMAND gdb -batch -x "${CMAKE_CURRENT_BINARY_DIR}/cell_trace.gdb" --args ./memory_profile_example
    DEPENDS memory_profile_example
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    COMMENT "Running GDB cell setup dynamic tracing..."
)

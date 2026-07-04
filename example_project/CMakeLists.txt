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

# ============================================================
# GDB Profiling Configuration (Local)
# ============================================================
set(CELL_SETUP_FUNC "complete_cell_setup" CACHE STRING "Name of the cell setup completion function to trace")
set(SCAN_SRC_DIR "${CMAKE_CURRENT_SOURCE_DIR}/inc" CACHE STRING "Directory to scan for structs/classes")

# Configure the local GDB script template
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

# Target for local dynamic breakpoint cell setup heap mapping
add_custom_target(trace-dynamic
    COMMAND gdb -batch -x "${CMAKE_CURRENT_BINARY_DIR}/cell_trace.gdb" --args ./memory_profile_example
    DEPENDS memory_profile_example
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    COMMENT "Running GDB cell setup dynamic tracing (local)..."
)

# Target for struct-aware dynamic heap allocation tracking
# malloc/operator new를 후킹하여 할당 크기 ↔ 구조체 크기를 매칭합니다.
add_custom_target(trace-dynamic-detailed
    COMMAND "${CMAKE_CURRENT_SOURCE_DIR}/../tools/memory_analyzer/auto_scan.sh" "${SCAN_SRC_DIR}" "structs_list.txt"
    COMMAND gdb -batch
        -ex "source ${CMAKE_CURRENT_SOURCE_DIR}/../tools/memory_analyzer/heap_tracker.py"
        -ex "run"
        -ex "quit"
        --args ./memory_profile_example
        > heap_alloc_report.txt
    DEPENDS memory_profile_example
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    COMMENT "Running struct-aware dynamic heap allocation tracking..."
)

# ============================================================
# Multi-Architecture / Multi-Server Remote Profiling
# ============================================================
# 사용법:
#   cmake .. -DENV_FILE=../../.env.sapphirerapids
#   cmake .. -DENV_FILE=../../.env.grace-c1
#   cmake .. -DENV_FILE=../../.env.skylake
#
# .env 프로필에 정의된 TARGET_IP, TARGET_PORT, GDB_BIN을 읽어
# 원격 GDB 스크립트를 동적으로 생성합니다.
# ============================================================

set(ENV_FILE "${CMAKE_CURRENT_SOURCE_DIR}/../.env" CACHE FILEPATH
    "Path to the server environment profile (.env, .env.grace-c1, .env.sapphirerapids, etc.)")

# --- .env 파일 파싱 ---
if(EXISTS "${ENV_FILE}")
    message(STATUS "Loading server profile: ${ENV_FILE}")
    file(STRINGS "${ENV_FILE}" _env_lines)

    # 기본값 설정 (파일에 정의되지 않은 경우 폴백)
    set(TARGET_IP "localhost")
    set(TARGET_PORT "9999")
    set(GDB_BIN "gdb")
    set(REMOTE_BINARY_PATH "/opt/vran/bin/vran_main")

    foreach(_line IN LISTS _env_lines)
        # 주석(#)과 빈 줄 건너뛰기
        if("${_line}" MATCHES "^#" OR "${_line}" STREQUAL "")
            continue()
        endif()

        # KEY=VALUE 형식 파싱
        if("${_line}" MATCHES "^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
            set(_key "${CMAKE_MATCH_1}")
            set(_val "${CMAKE_MATCH_2}")
            set(${_key} "${_val}")
            message(STATUS "  ${_key} = ${_val}")
        endif()
    endforeach()
else()
    message(WARNING "Environment file not found: ${ENV_FILE}")
    message(WARNING "Using defaults: TARGET_IP=localhost, TARGET_PORT=9999, GDB_BIN=gdb")
    set(TARGET_IP "localhost")
    set(TARGET_PORT "9999")
    set(GDB_BIN "gdb")
    set(REMOTE_BINARY_PATH "/opt/vran/bin/vran_main")
endif()

# .env에서 CELL_SETUP_FUNC가 오버라이드된 경우 반영
if(DEFINED CELL_SETUP_FUNC)
    message(STATUS "  CELL_SETUP_FUNC = ${CELL_SETUP_FUNC}")
endif()

# --- 원격 GDB 스크립트 동적 생성 ---
configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/../tools/memory_analyzer/remote_trace.gdb.in"
    "${CMAKE_CURRENT_BINARY_DIR}/remote_trace.gdb"
    @ONLY
)

message(STATUS "Generated remote_trace.gdb for ${TARGET_IP}:${TARGET_PORT} using ${GDB_BIN}")

# --- 원격 동적 추적 타겟 ---
# gdbserver가 원격 서버에서 실행 중이어야 합니다:
#   (원격서버)$ gdbserver :9999 /opt/vran/bin/vran_main
add_custom_target(trace-dynamic-remote
    COMMAND ${GDB_BIN} -batch -x "${CMAKE_CURRENT_BINARY_DIR}/remote_trace.gdb"
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    COMMENT "Running remote GDB dynamic tracing on ${TARGET_IP}:${TARGET_PORT} via ${GDB_BIN}..."
)

# --- 원격 정적 분석 타겟 ---
# 원격 서버의 바이너리를 로컬로 복사(scp)한 뒤 DWARF 구조체 분석 실행
add_custom_target(trace-static-remote
    COMMAND "${CMAKE_CURRENT_SOURCE_DIR}/../tools/memory_analyzer/auto_scan.sh" "${SCAN_SRC_DIR}" "structs_list.txt"
    COMMAND ${GDB_BIN} -batch -ex "source ${CMAKE_CURRENT_SOURCE_DIR}/../tools/memory_analyzer/analyze_struct.py" -ex "quit" ./memory_profile_example > struct_report_remote.txt
    DEPENDS memory_profile_example
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    COMMENT "Generating remote static structures layout report via ${GDB_BIN}..."
)

# --- 서버 프로필 정보 출력 타겟 (디버깅/확인용) ---
add_custom_target(show-profile
    COMMAND ${CMAKE_COMMAND} -E echo "========================================"
    COMMAND ${CMAKE_COMMAND} -E echo " Active Server Profile"
    COMMAND ${CMAKE_COMMAND} -E echo "========================================"
    COMMAND ${CMAKE_COMMAND} -E echo "  ENV_FILE:           ${ENV_FILE}"
    COMMAND ${CMAKE_COMMAND} -E echo "  TARGET_IP:          ${TARGET_IP}"
    COMMAND ${CMAKE_COMMAND} -E echo "  TARGET_PORT:        ${TARGET_PORT}"
    COMMAND ${CMAKE_COMMAND} -E echo "  GDB_BIN:            ${GDB_BIN}"
    COMMAND ${CMAKE_COMMAND} -E echo "  REMOTE_BINARY_PATH: ${REMOTE_BINARY_PATH}"
    COMMAND ${CMAKE_COMMAND} -E echo "  CELL_SETUP_FUNC:    ${CELL_SETUP_FUNC}"
    COMMAND ${CMAKE_COMMAND} -E echo "========================================"
    COMMENT "Showing active server profile..."
)


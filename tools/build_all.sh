#!/bin/bash
set -e

# Base directory of the repository
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Function to build, run pahole, and push metrics
build_and_push() {
    local COMPILER="$1"
    local ARCH="$2"
    local CC_BIN="$3"
    local CXX_BIN="$4"
    local BUILD_DIR="${BASE_DIR}/build_${COMPILER}_${ARCH}"

    echo "=== Building for ${COMPILER} (${ARCH}) ==="
    mkdir -p "${BUILD_DIR}"
    cd "${BUILD_DIR}"

    # Configure CMake
    if [ "${ARCH}" = "arm64" ]; then
        cmake -DCMAKE_SYSTEM_NAME=Linux \
              -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
              -DCMAKE_C_COMPILER="${CC_BIN}" \
              -DCMAKE_CXX_COMPILER="${CXX_BIN}" \
              "${BASE_DIR}/example_project"
    else
        CC="${CC_BIN}" CXX="${CXX_BIN}" cmake "${BASE_DIR}/example_project"
    fi

    # Build
    make -j$(nproc)

    # Run pahole, parse, and push metrics
    echo "=== Parsing & Pushing metrics for ${COMPILER} (${ARCH}) ==="
    find . -name "*.o" | xargs pahole > pahole_output.txt
    python3 "${BASE_DIR}/tools/parse_pahole.py" pahole_output.txt > parsed_metrics.json
    python3 "${BASE_DIR}/tools/push_metrics.py" --backend influxdb --compiler "${COMPILER}" --arch "${ARCH}" parsed_metrics.json
    
    cd "${BASE_DIR}"
}

# 1. GCC x86_64
build_and_push "gcc" "x86_64" "gcc" "g++"

# 2. Clang x86_64
build_and_push "clang" "x86_64" "clang" "clang++"

# 3. GCC ARM64
build_and_push "gcc" "arm64" "aarch64-linux-gnu-gcc" "aarch64-linux-gnu-g++"

echo "=== All builds, parsing, and pushing completed successfully! ==="

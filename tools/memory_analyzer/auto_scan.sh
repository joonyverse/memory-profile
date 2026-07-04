#!/bin/bash
# auto_scan.sh: Extract struct/class names from C++ headers using regex

SRC_DIR="$1"
OUT_FILE="$2"
if [ -z "$SRC_DIR" ]; then
    SRC_DIR="."
fi

NAMES=$(find "$SRC_DIR" -type f \( -name "*.h" -o -name "*.hpp" -o -name "*.cpp" \) | while read -r file; do
    grep -E "^\s*(struct|class)\s+\w+" "$file" | while read -r line; do
        if [[ "$line" =~ \;$ ]]; then
            continue
        fi
        name=$(echo "$line" | sed -E "s/^\s*(struct|class)\s+(\w+).*/\2/")
        if [ -n "$name" ] && [ "$name" != "alignas" ]; then
            echo "$name"
        fi
    done
done | sort -u)

if [ -n "$OUT_FILE" ]; then
    echo "$NAMES" > "$OUT_FILE"
else
    echo "$NAMES"
fi

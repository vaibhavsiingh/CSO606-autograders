#!/usr/bin/env bash
# Uses awk instead of sed — should trigger missing required sed
mkdir -p "$2"
: > "$2/patched_files.txt"
find "$1" -type f \( -name '*.c' -o -name '*.h' \) | while read -r f; do
    if grep -q '#include <oldlib.h>' "$f" && grep -q 'init_adapter(' "$f"; then
        cp "$f" "${f}.bak"
        awk '{gsub(/#include <oldlib.h>/, "#include <newlib.h>"); print}' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
        echo "$f" >> "$2/patched_files.txt"
    fi
done
sort -o "$2/patched_files.txt" "$2/patched_files.txt"

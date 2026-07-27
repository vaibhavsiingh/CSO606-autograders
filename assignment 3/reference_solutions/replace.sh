#!/usr/bin/env bash
# replace.sh <src_dir> <output_dir>
# In every *.c/*.h under <src_dir> (any depth) that contains BOTH
# "#include <oldlib.h>" AND a call to init_adapter(), replaces the include
# with "#include <newlib.h>", backs up the original to <file>.bak, and
# lists the modified file in <output_dir>/patched_files.txt (sorted).
set -euo pipefail

src_dir="$1"
outdir="$2"
mkdir -p "$outdir"
: > "$outdir/patched_files.txt"

while IFS= read -r -d '' f; do
    if grep -qF '#include <oldlib.h>' "$f" && grep -q 'init_adapter(' "$f"; then
        cp "$f" "${f}.bak"
        sed -i 's|#include <oldlib\.h>|#include <newlib.h>|' "$f"
        echo "$f" >> "$outdir/patched_files.txt"
    fi
done < <(find "$src_dir" -type f \( -name '*.c' -o -name '*.h' \) -print0)

sort -o "$outdir/patched_files.txt" "$outdir/patched_files.txt"

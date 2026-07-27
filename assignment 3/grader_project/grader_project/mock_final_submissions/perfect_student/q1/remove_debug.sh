#!/usr/bin/env bash
# remove_debug.sh <src_dir> <output_dir>
# Removes every line beginning with "// TEMPDEBUG:" from all *.c and *.h
# files under <src_dir>, recursively. Robust to paths with spaces.
# Writes <output_dir>/debug_removed_count.txt with the total removed count.
set -euo pipefail

src_dir="$1"
outdir="$2"
mkdir -p "$outdir"

total=0

while IFS= read -r -d '' f; do
    cnt=$(grep -c '^// TEMPDEBUG:' "$f" || true)
    if [ "$cnt" -gt 0 ]; then
        sed -i '/^\/\/ TEMPDEBUG:/d' "$f"
        total=$((total + cnt))
    fi
done < <(find "$src_dir" -type f \( -name '*.c' -o -name '*.h' \) -print0)

echo "$total" > "$outdir/debug_removed_count.txt"

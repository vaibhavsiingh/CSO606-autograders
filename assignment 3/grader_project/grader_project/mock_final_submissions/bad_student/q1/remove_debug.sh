#!/usr/bin/env bash
mkdir -p "$2"
total=0
while IFS= read -r -d '' f; do
    cnt=$(grep -c '^// TEMPDEBUG:' "$f" || true)
    if [ "$cnt" -gt 0 ]; then
        sed -i '/^\/\/ TEMPDEBUG:/d' "$f"
        total=$((total + cnt))
    fi
done < <(find "$1" -type f \( -name '*.c' -o -name '*.h' \) -print0)
echo "$total" > "$2/debug_removed_count.txt"

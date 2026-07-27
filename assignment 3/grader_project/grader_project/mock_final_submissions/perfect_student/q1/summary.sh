#!/usr/bin/env bash
# summary.sh <input> <output>
# Top 10 failed usernames by count (desc); ties broken alphabetically (asc).
# Output: <output>/top_failed_users.txt, one "username count" per line.
#
# Uses awk both to extract usernames AND to compute the frequency table,
# as required by the problem ("must use awk ... to extract ... and to compute").
# Same field-position logic as failed_login.sh.
set -euo pipefail

input="$1"
outdir="$2"
mkdir -p "$outdir"

awk '/Failed password for/ {
    user = ($9 == "invalid") ? $11 : $9
    count[user]++
}
END {
    for (u in count) print u, count[u]
}' "$input" | sort -k2,2nr -k1,1 | head -n 10 > "$outdir/top_failed_users.txt"

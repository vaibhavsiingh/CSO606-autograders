#!/usr/bin/env bash
# local_filter.sh <input> <output>
# Filters ERROR lines from app.log. Prints "<date> <time> <error_code>".
# Error code is identified by the field matching "code=E<digits>"; the
# field position varies per record. Only the value (E<digits>) is printed,
# not the "code=" prefix. Lines containing ERROR but no code= field are skipped.
set -euo pipefail

input="$1"
outdir="$2"
mkdir -p "$outdir"

awk '/ERROR/ {
    code = ""
    for (i = 3; i <= NF; i++) {
        if ($i ~ /^code=E[0-9]+$/) {
            split($i, a, "=")
            code = a[2]
            break
        }
    }
    if (code != "") print $1, $2, code
}' "$input" > "$outdir/error_lines.txt"

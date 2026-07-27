#!/usr/bin/env bash
# Generates expected output for every script × test case from the reference
# solutions. Re-running this OVERWRITES expected/ — only do that intentionally.
# Usage: ./generate_expected.sh
set -euo pipefail
cd "$(dirname "$0")/.."       # repo root

REF=reference_solutions
TC=testcases

chmod +x "$REF"/*.sh

# ---- helper: run reference in a temp dir, capture output ---- #
run_read_only() {
    # run_read_only <script> <outdir> <extra_args...>
    local script="$1" outdir="$2"; shift 2
    bash "$REF/$script" "$@" "$outdir"
}

run_mutating() {
    # run_mutating <script> <src_input_dir> <outdir>
    # Copies input to a temp dir (script mutates "src/"), runs there.
    local script="$1" src_input="$2" outdir="$3"
    local tmp abs_outdir
    tmp=$(mktemp -d)
    abs_outdir=$(realpath "$outdir" 2>/dev/null || { mkdir -p "$outdir"; realpath "$outdir"; })
    cp -r "$src_input/src" "$tmp/src"
    mkdir -p "$abs_outdir"
    (cd "$tmp" && bash /home/claude/grader_project/"$REF/$script" "src" "$abs_outdir")
    rm -rf "$tmp"
}

# ---- failed_login ---- #
for tc in tc1 tc2 tc3; do
    outdir="$TC/failed_login/$tc/expected"
    mkdir -p "$outdir"
    run_read_only failed_login.sh "$outdir" \
        "$TC/failed_login/$tc/input/auth.log"
    echo "failed_login/$tc: $(wc -l < "$outdir/failed_logins.txt") lines"
done

# ---- summary ---- #
for tc in tc1 tc2 tc3; do
    outdir="$TC/summary/$tc/expected"
    mkdir -p "$outdir"
    run_read_only summary.sh "$outdir" \
        "$TC/summary/$tc/input/auth.log"
    echo "summary/$tc: $(wc -l < "$outdir/top_failed_users.txt") lines"
done

# ---- local_filter ---- #
for tc in tc1 tc2 tc3; do
    outdir="$TC/local_filter/$tc/expected"
    mkdir -p "$outdir"
    run_read_only local_filter.sh "$outdir" \
        "$TC/local_filter/$tc/input/app.log"
    echo "local_filter/$tc: $(wc -l < "$outdir/error_lines.txt") lines"
done

# ---- replace ---- #
for tc in tc1 tc2 tc3; do
    outdir="$TC/replace/$tc/expected"
    run_mutating replace.sh "$TC/replace/$tc/input" "$outdir"
    echo "replace/$tc patched: $(cat "$outdir/patched_files.txt")"
done

# ---- remove_debug ---- #
for tc in tc1 tc2 tc3; do
    outdir="$TC/remove_debug/$tc/expected"
    run_mutating remove_debug.sh "$TC/remove_debug/$tc/input" "$outdir"
    echo "remove_debug/$tc count: $(cat "$outdir/debug_removed_count.txt")"
done

echo ""
echo "All expected outputs generated."

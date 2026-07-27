#!/usr/bin/env bash
# Doesn't use awk at all — uses grep+cut
mkdir -p "$2"
grep ERROR "$1" | awk '{print $1, $2}' > "$2/error_lines.txt"
# Missing error code field — output will be wrong but awk IS used here

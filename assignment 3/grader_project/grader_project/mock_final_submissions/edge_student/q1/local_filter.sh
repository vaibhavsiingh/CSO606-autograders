#!/usr/bin/env bash
mkdir -p "$2"
# Forgets to write error_lines.txt
echo "oops" > "$2/wrong_name.txt"

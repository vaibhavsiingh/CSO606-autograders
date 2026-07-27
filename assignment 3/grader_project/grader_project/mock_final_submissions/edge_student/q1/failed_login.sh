#!/usr/bin/env bash
awk '/Failed password for/ { print $1, $2, $3' "$1" > "$2/failed_logins.txt"

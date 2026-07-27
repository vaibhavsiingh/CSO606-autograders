#!/usr/bin/env bash
# Mostly correct but doesn't handle "invalid user" → username will be "invalid"
awk '/Failed password for/ { print $1, $2, $3, $9, $11 }' "$1" > "$2/failed_logins.txt"

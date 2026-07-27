#!/usr/bin/env bash
# failed_login.sh <input> <output>
# Extracts failed SSH login lines from auth.log.
# Output: <output>/failed_logins.txt, fields: month day time username source_ip
#
# Handles both forms in the log:
#   ... Failed password for root from 10.5.12.77 port 51322 ssh2
#   ... Failed password for invalid user guest from 185.199.108.7 port 59201 ssh2
#
# Fixed field layout (1-indexed, same for both forms):
#   $1=month $2=day $3=time $4=host $5=sshd[PID]:
#   $6=Failed $7=password $8=for
#   Normal case:       $9=username  $10=from  $11=IP
#   Invalid user case: $9=invalid   $10=user  $11=username  $12=from  $13=IP
set -euo pipefail

input="$1"
outdir="$2"
mkdir -p "$outdir"

awk '/Failed password for/ {
    if ($9 == "invalid")
        print $1, $2, $3, $11, $13
    else
        print $1, $2, $3, $9, $11
}' "$input" > "$outdir/failed_logins.txt"

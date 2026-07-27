#!/usr/bin/env bash
# Uses python - FORBIDDEN
mkdir -p "$2"
python3 - "$1" "$2" <<'PY'
import sys, collections
counts = collections.Counter()
with open(sys.argv[1]) as f:
    for line in f:
        if "Failed password for" in line:
            parts = line.split()
            idx = parts.index("for")
            user = parts[idx+2] if parts[idx+1] == "invalid" else parts[idx+1]
            counts[user] += 1
with open(sys.argv[2]+"/top_failed_users.txt","w") as f:
    for u,c in sorted(counts.most_common(10), key=lambda x:(-x[1],x[0])):
        f.write(f"{u} {c}\n")
PY

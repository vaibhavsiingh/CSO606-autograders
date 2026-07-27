#!/usr/bin/env bash
# Builds every fixture under testcases/. Re-run any time to regenerate from
# scratch (it wipes testcases/<script>/tc*/input first).
set -euo pipefail
cd "$(dirname "$0")"

mk() { mkdir -p "$1"; }

# ---------------------------------------------------------------- #
# failed_login : input is a single auth.log file
# ---------------------------------------------------------------- #
for tc in tc1 tc2 tc3; do
    rm -rf "failed_login/$tc/input"
    mk "failed_login/$tc/input"
done

cat > failed_login/tc1/input/auth.log <<'EOF'
Jul 10 08:11:09 labnode42 sshd[1800]: Failed password for root from 10.5.12.77 port 51322 ssh2
Jul 10 08:11:10 labnode42 sshd[1801]: Accepted password for alice from 10.5.12.9 port 51330 ssh2
Jul 10 08:11:09 labnode42 sshd[1900]: Failed password for invalid user guest from 185.199.108.7 port 59201 ssh2
Jul 10 08:12:01 labnode42 sshd[1802]: Connection closed by 10.5.12.9 port 51330
Jul 10 08:13:45 labnode42 sshd[1903]: Failed password for invalid user admin from 203.0.113.5 port 41001 ssh2
EOF

cat > failed_login/tc2/input/auth.log <<'EOF'
Aug 02 23:59:58 db01 sshd[2201]: Failed password for root from 198.51.100.4 port 33012 ssh2
Aug 02 23:59:59 db01 sshd[2202]: Failed password for root from 198.51.100.4 port 33015 ssh2
Aug 03 00:00:01 db01 sshd[2203]: Failed password for invalid user backup from 198.51.100.4 port 33020 ssh2
Aug 03 00:00:05 db01 sshd[2204]: Failed password for invalid user backup from 192.0.2.77 port 40500 ssh2
Aug 03 00:00:09 db01 sshd[2205]: Failed password for postgres from 192.0.2.77 port 40510 ssh2
Aug 03 00:01:00 db01 sshd[2206]: Accepted publickey for deploy from 192.0.2.77 port 40520 ssh2
EOF

cat > failed_login/tc3/input/auth.log <<'EOF'
Jan 01 00:00:01 edge1 sshd[1]: Failed password for invalid user oracle from 10.0.0.1 port 1 ssh2
Jan 01 00:00:02 edge1 sshd[2]: Failed password for invalid user oracle from 10.0.0.2 port 2 ssh2
Jan 01 00:00:03 edge1 sshd[3]: pam_unix(sshd:auth): authentication failure
Jan 01 00:00:04 edge1 sshd[4]: Failed password for root from 10.0.0.3 port 3 ssh2
Jan 01 00:00:05 edge1 sshd[5]: Failed password for invalid user test from 10.0.0.4 port 4 ssh2
Jan 01 00:00:06 edge1 sshd[6]: Disconnected from 10.0.0.4 port 4
EOF

# ---------------------------------------------------------------- #
# summary : input is a single auth.log file (needs enough distinct
# users / ties / >10 users to exercise the ranking logic)
# ---------------------------------------------------------------- #
for tc in tc1 tc2 tc3; do
    rm -rf "summary/$tc/input"
    mk "summary/$tc/input"
done

cat > summary/tc1/input/auth.log <<'EOF'
Mar 01 01:00:00 h sshd[1]: Failed password for root from 1.1.1.1 port 1 ssh2
Mar 01 01:00:01 h sshd[2]: Failed password for root from 1.1.1.2 port 1 ssh2
Mar 01 01:00:02 h sshd[3]: Failed password for root from 1.1.1.3 port 1 ssh2
Mar 01 01:00:03 h sshd[4]: Failed password for invalid user guest from 1.1.1.4 port 1 ssh2
Mar 01 01:00:04 h sshd[5]: Failed password for invalid user admin from 1.1.1.5 port 1 ssh2
EOF

# tc2: deliberate ties -> "admin" and "guest" both count 2, "root" count 3
cat > summary/tc2/input/auth.log <<'EOF'
Apr 01 01:00:00 h sshd[1]: Failed password for root from 2.2.2.1 port 1 ssh2
Apr 01 01:00:01 h sshd[2]: Failed password for root from 2.2.2.2 port 1 ssh2
Apr 01 01:00:02 h sshd[3]: Failed password for root from 2.2.2.3 port 1 ssh2
Apr 01 01:00:03 h sshd[4]: Failed password for invalid user guest from 2.2.2.4 port 1 ssh2
Apr 01 01:00:04 h sshd[5]: Failed password for invalid user guest from 2.2.2.5 port 1 ssh2
Apr 01 01:00:05 h sshd[6]: Failed password for invalid user admin from 2.2.2.6 port 1 ssh2
Apr 01 01:00:06 h sshd[7]: Failed password for invalid user admin from 2.2.2.7 port 1 ssh2
EOF

# tc3: 13 distinct users so the top-10 cutoff is actually exercised, with a
# tie straddling the 10th/11th place boundary (user10 and user11 both =1)
python3 - <<'PY'
import random
lines = []
counts = {
    "root": 9, "oracle": 8, "postgres": 7, "deploy": 6, "backup": 5,
    "guest": 4, "admin": 3, "test": 2, "ftp": 2,
    "user10": 1, "user11": 1, "user12": 1, "user13": 1,
}
i = 0
for user, c in counts.items():
    for _ in range(c):
        i += 1
        lines.append(f"May 01 02:00:{i%60:02d} h sshd[{i}]: Failed password for invalid user {user} from 3.3.3.{i%250+1} port 1 ssh2")
with open("summary/tc3/input/auth.log", "w") as f:
    f.write("\n".join(lines) + "\n")
PY

# ---------------------------------------------------------------- #
# local_filter : input is a single app.log file. Error-code is a field
# in "code=E<digits>" format; its position shifts between records.
# Lines with ERROR but no code= field must be silently skipped.
# ---------------------------------------------------------------- #
for tc in tc1 tc2 tc3; do
    rm -rf "local_filter/$tc/input"
    mk "local_filter/$tc/input"
done

# tc1: normal case — code= at different field positions across lines;
# one INFO line and one WARN line must be ignored.
cat > local_filter/tc1/input/app.log <<'EOF'
2024-07-10 08:15:22 INFO svc=auth msg="Starting service"
2024-07-10 08:15:23 ERROR svc=auth code=E1001 msg="Connection refused"
2024-07-10 08:16:01 ERROR db code=E2002 msg="timeout waiting for response"
2024-07-10 08:16:45 ERROR cache extra1 extra2 code=E3003 msg="cache miss exceeded threshold"
2024-07-10 08:17:00 WARN svc=auth msg="retry scheduled"
EOF

# tc2: ERROR line with no code= field (must be skipped); a non-ERROR line
# that contains the substring "ERROR" must also be skipped.
cat > local_filter/tc2/input/app.log <<'EOF'
2024-08-01 00:00:01 DEBUG ERRORHANDLER config=default
2024-08-01 00:00:02 ERROR svc=api code=E4004 msg="malformed request"
2024-08-01 00:00:03 INFO svc=api msg="no issues"
2024-08-01 00:00:04 ERROR svc=billing region=us code=E5005 msg="ledger mismatch"
2024-08-01 00:00:05 ERROR msg="unparseable line with no code field at all"
EOF

# tc3: verify the error code value is extracted (not the whole key=value token);
# short code value; code deep in the line; WARN line with code= must be skipped.
cat > local_filter/tc3/input/app.log <<'EOF'
2024-09-09 12:00:00 INFO msg="startup complete"
2024-09-09 12:00:01 ERROR svc=gw code=E10 msg="short code"
2024-09-09 12:00:02 ERROR a b c d e code=E999999 msg="long preamble"
2024-09-09 12:00:03 WARN svc=gw code=E1234 msg="warn lines must be excluded"
2024-09-09 12:00:04 ERROR svc=gw code=E6006 msg="gateway down"
EOF

# ---------------------------------------------------------------- #
# replace : input is a "src" directory tree (the hardcoded name)
# ---------------------------------------------------------------- #
for tc in tc1 tc2 tc3; do
    rm -rf "replace/$tc/input"
    mk "replace/$tc/input/src"
done

# tc1: one qualifying file (both include + init_adapter), one file with the
# include but NO init_adapter call (must NOT be touched), one file with
# init_adapter but NOT the include (must NOT be touched), one untouched file.
mk replace/tc1/input/src/module1/io
cat > replace/tc1/input/src/module1/io/parser.c <<'EOF'
#include <oldlib.h>
#include <stdio.h>

void parse(void) {
    init_adapter();
}
EOF

cat > replace/tc1/input/src/module1/io/file_reader.c <<'EOF'
#include <oldlib.h>
#include <stdio.h>

void read_file(void) {
    /* no adapter init here */
}
EOF

mk replace/tc1/input/src/include/core
cat > replace/tc1/input/src/include/core/adapter.h <<'EOF'
#ifndef ADAPTER_H
#define ADAPTER_H
void init_adapter(void);
#endif
EOF

cat > replace/tc1/input/src/module1/io/init_sequence.c <<'EOF'
#include <stdio.h>

void boot(void) {
    init_adapter();
}
EOF

# tc2: deeper nesting + multiple qualifying files in different subtrees,
# including a .h file that qualifies with a real call (depth must not be
# assumed fixed). Also includes a file that has oldlib but NO init_adapter
# call at all (recovery.c) and a header with only a declaration (no call).
mk replace/tc2/input/src/legacy/net
cat > replace/tc2/input/src/legacy/net/adapter_boot.c <<'EOF'
#include <oldlib.h>
#include "adapter_reset.h"

void adapter_boot(void) {
    init_adapter();
}
EOF

# This .h file has #include <oldlib.h> AND an actual inline call — qualifies.
cat > replace/tc2/input/src/legacy/net/adapter_reset.h <<'EOF'
#include <oldlib.h>

static inline void do_reset(void) {
    init_adapter();
}
EOF

# This header has only a DECLARATION of init_adapter, NOT a call, and no oldlib.
# It must NOT be touched.
cat > replace/tc2/input/src/legacy/net/connection.h <<'EOF'
#ifndef CONNECTION_H
#define CONNECTION_H
void init_adapter(void);   /* declaration only — no call, no oldlib */
#endif
EOF

mk replace/tc2/input/src/module2/drivers/usb
cat > replace/tc2/input/src/module2/drivers/usb/adapter_probe.c <<'EOF'
#include <oldlib.h>
#include "adapter_probe.h"

int probe(void) {
    return init_adapter();
}
EOF

mk replace/tc2/input/src/module2/drivers/serial/subsys
cat > replace/tc2/input/src/module2/drivers/serial/subsys/recovery.c <<'EOF'
#include <oldlib.h>

void recover(void) {
    /* does not call init_adapter */
}
EOF

# tc3: a file that already uses newlib.h (no-op), a file with the include
# appearing alongside other includes, and confirm only-oldlib-no-call files
# are skipped, at a single-file-deep level (no extra nesting needed here).
mk replace/tc3/input/src/moduleA
cat > replace/tc3/input/src/moduleA/http_client.c <<'EOF'
#include <oldlib.h>
#include <string.h>
#include <stdlib.h>

static void setup(void) {
    init_adapter();
}
EOF

cat > replace/tc3/input/src/moduleA/already_new.c <<'EOF'
#include <newlib.h>

void already_migrated(void) {
    init_adapter();
}
EOF

cat > replace/tc3/input/src/moduleA/unrelated.h <<'EOF'
#ifndef UNRELATED_H
#define UNRELATED_H
int unrelated(void);
#endif
EOF

# ---------------------------------------------------------------- #
# remove_debug : input is a "src" directory tree (hardcoded name)
# ---------------------------------------------------------------- #
for tc in tc1 tc2 tc3; do
    rm -rf "remove_debug/$tc/input"
    mk "remove_debug/$tc/input/src"
done

mk remove_debug/tc1/input/src/module1/io
cat > remove_debug/tc1/input/src/module1/io/file_reader.c <<'EOF'
// TEMPDEBUG: entering file_reader
#include <stdio.h>

void read_file(void) {
// TEMPDEBUG: about to open file
    FILE *f = fopen("x", "r");
// TEMPDEBUG: opened
}
EOF

mk remove_debug/tc1/input/src/include/moduleB
cat > remove_debug/tc1/input/src/include/moduleB/metrics.h <<'EOF'
#ifndef METRICS_H
#define METRICS_H
// TEMPDEBUG: header guard check
int metric_count(void);
#endif
EOF

cat > remove_debug/tc1/input/src/module1/io/init_helpers.h <<'EOF'
#ifndef INIT_HELPERS_H
#define INIT_HELPERS_H
int init_helper(void);
#endif
EOF

# tc2: path containing spaces (explicit robustness requirement) + nested dirs.
mk "remove_debug/tc2/input/src/module2/drivers/serial"
cat > "remove_debug/tc2/input/src/module2/drivers/serial/serial_boot.c" <<'EOF'
// TEMPDEBUG: serial boot start
#include <stdio.h>
void serial_boot(void) {
    int x = 1;
}
// TEMPDEBUG: serial boot end
EOF

mk "remove_debug/tc2/input/src/module2/drivers/serial/needs space"
cat > "remove_debug/tc2/input/src/module2/drivers/serial/needs space/serial_diag.c" <<'EOF'
// TEMPDEBUG: diag entry
#include <stdio.h>
// TEMPDEBUG: diag middle
void serial_diag(void) {
    int y = 2;
}
EOF

cat > "remove_debug/tc2/input/src/module2/drivers/serial/needs space/serial_diag.h" <<'EOF'
#ifndef SERIAL_DIAG_H
#define SERIAL_DIAG_H
// TEMPDEBUG: header marker
void serial_diag(void);
#endif
EOF

# tc3: consecutive TEMPDEBUG lines, one at very first line, one at very last
# line (no trailing newline issues), and a file with zero matches.
mk remove_debug/tc3/input/src/module2/tools
cat > remove_debug/tc3/input/src/module2/tools/report.c <<'EOF'
// TEMPDEBUG: first line marker
// TEMPDEBUG: second consecutive marker
#include <stdio.h>

void report(void) {
    printf("report\n");
}
// TEMPDEBUG: last line marker
EOF

cat > remove_debug/tc3/input/src/module2/tools/clean.c <<'EOF'
#include <stdio.h>

void clean(void) {
    printf("nothing to remove here\n");
}
EOF

echo "Fixtures built."

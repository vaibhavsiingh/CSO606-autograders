# config.py — edit this to change marks, weights, and tool-policy rules.
# The grader imports this directly; no other file needs to be touched.

# ── marks per script ─────────────────────────────────────────────────────────
MAX_MARKS = {
    "failed_login": 5,
    "summary":      5,
    "local_filter": 5,
    "replace":      5,
    "remove_debug": 5,
}

# ── per-testcase weights ──────────────────────────────────────────────────────
# Weights within each script must sum to 1.0 for MAX_MARKS to be the literal
# ceiling.  A student's mark for a script = MAX_MARKS[s] × Σ weight[tc]
# for every test case that passes.
TC_WEIGHTS = {
    "failed_login": {"tc1": 0.30, "tc2": 0.40, "tc3": 0.30},
    "summary":      {"tc1": 0.30, "tc2": 0.30, "tc3": 0.40},
    "local_filter": {"tc1": 0.30, "tc2": 0.30, "tc3": 0.40},
    "replace":      {"tc1": 0.25, "tc2": 0.50, "tc3": 0.25},
    "remove_debug": {"tc1": 0.25, "tc2": 0.50, "tc3": 0.25},
}

# ── tool-use requirements ─────────────────────────────────────────────────────
# Scripts in REQUIRES_AWK must contain a literal `awk` call; same for sed.
# A script that passes all test cases but is missing its required tool is
# zeroed entirely.  Set ENFORCE_REQUIRED_TOOLS = False to skip this check.
ENFORCE_REQUIRED_TOOLS = True

REQUIRES_AWK = {"failed_login", "summary", "local_filter"}
REQUIRES_SED = {"replace", "remove_debug"}

# ── forbidden tools ───────────────────────────────────────────────────────────
# Each distinct forbidden interpreter found in a script costs FORBIDDEN_PENALTY
# marks (floor: 0).  Finding one tool once = one penalty, even if called
# multiple times.
FORBIDDEN_TOOLS    = ["python3", "perl", "ruby", "Rscript",
                      "node", "nodejs", "php"]
FORBIDDEN_PENALTY  = 1.0   # marks deducted per distinct forbidden tool

# ── execution ─────────────────────────────────────────────────────────────────
TIMEOUT = 15   # seconds per test-case run

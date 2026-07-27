#!/usr/bin/env python3
"""
grade_all.py — Q1 (bash/sed/awk) submission grader
Usage:
    python3 grade_all.py [--submissions DIR] [--testcases DIR] [--output DIR]

Defaults:
    --submissions  ./final_submissions
    --testcases    ./testcases
    --output       ./grader_output

Outputs:
    <output>/grades.csv               one row per student
    <output>/per_student/<id>.txt     full per-script breakdown
"""

import argparse
import csv
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ── load config ───────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from config import (
    MAX_MARKS, TC_WEIGHTS,
    ENFORCE_REQUIRED_TOOLS, REQUIRES_AWK, REQUIRES_SED,
    FORBIDDEN_TOOLS, FORBIDDEN_PENALTY,
    TIMEOUT,
)

SCRIPTS  = ["failed_login", "summary", "local_filter", "replace", "remove_debug"]
TCS      = ["tc1", "tc2", "tc3"]
MUTATING = {"replace", "remove_debug"}   # scripts that hardcode "src/"


# ─────────────────────────────────────────────────────────────────────────────
# Tool checker
# ─────────────────────────────────────────────────────────────────────────────

def check_tools(script_file: Path, script_key: str) -> list[str]:
    """
    Returns a list of short issue strings (empty = clean).
    Checks for forbidden interpreters and missing required awk/sed.
    """
    issues = []
    text   = script_file.read_text(errors="replace")

    # Forbidden tools — one penalty per distinct tool, not per occurrence.
    # Word-boundary anchor after the tool name prevents "python" matching
    # inside "python3".
    for tool in FORBIDDEN_TOOLS:
        pattern = rf'(?:^|[\s/]){re.escape(tool)}\b'
        if re.search(pattern, text, re.MULTILINE):
            issues.append(f"uses {tool} (forbidden)")

    if not ENFORCE_REQUIRED_TOOLS:
        return issues

    if script_key in REQUIRES_AWK and not re.search(r'\bawk\b', text):
        issues.append("missing required awk")
    if script_key in REQUIRES_SED and not re.search(r'\bsed\b', text):
        issues.append("missing required sed")

    return issues


# ─────────────────────────────────────────────────────────────────────────────
# Script runners
# ─────────────────────────────────────────────────────────────────────────────

def run_readonly(script: Path, input_file: Path, out_dir: Path) -> tuple[int, str]:
    """Run a script that takes <input_file> <output_dir>."""
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run(
            ["bash", str(script), str(input_file), str(out_dir)],
            capture_output=True, timeout=TIMEOUT, text=True,
        )
        return r.returncode, r.stderr[:300]
    except subprocess.TimeoutExpired:
        return -1, "timeout"


def run_mutating(script: Path, tc_input: Path, out_dir: Path) -> tuple[int, str]:
    """
    Run replace.sh / remove_debug.sh.
    Students write: ./replace.sh <src_dir> <output_dir>
    We copy tc_input/src → sandbox/src, then call:
        bash script "src" /abs/path/to/output
    from inside the sandbox, so $1 is a relative "src" path (matching what
    students see when they run from q1_inputs/) and file paths in
    patched_files.txt come out as "src/..." naturally.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    abs_out = out_dir.resolve()
    sandbox = Path(tempfile.mkdtemp())
    try:
        shutil.copytree(tc_input / "src", sandbox / "src")
        r = subprocess.run(
            ["bash", str(script.resolve()), "src", str(abs_out)],
            capture_output=True, timeout=TIMEOUT, text=True,
            cwd=str(sandbox),
        )
        return r.returncode, r.stderr[:300]
    except subprocess.TimeoutExpired:
        return -1, "timeout"
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


# ─────────────────────────────────────────────────────────────────────────────
# Per-testcase grading
# ─────────────────────────────────────────────────────────────────────────────

def normalize_output(script_key: str, text: str) -> str:
    """
    Normalize output before comparison to handle format variations the
    problem statement does not explicitly rule out.

    summary.sh: the problem specifies 'top 10 usernames' but does NOT
    specify whether the count appears first or second on each line.
    Both 'username count' and 'count username' are accepted.
    Normalise to 'username count' by detecting which token is purely
    numeric (the count).
    """
    if script_key != "summary":
        return text
    lines = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].isdigit():
            lines.append(f"{parts[1]} {parts[0]}")   # count username → username count
        else:
            lines.append(line)
    result = "\n".join(lines)
    if text.endswith("\n"):
        result += "\n"
    return result


def grade_tc(script_key: str, tc: str, script_file: Path,
             tc_base: Path) -> str:
    """
    Returns "PASS" or a one-phrase failure reason.
    tc_base is the testcases/<script>/ directory.
    """
    tc_in        = tc_base / tc / "input"
    expected_dir = tc_base / tc / "expected"
    out_dir      = Path(tempfile.mkdtemp())

    try:
        if script_key in ("failed_login", "summary"):
            rc, _ = run_readonly(script_file, tc_in / "auth.log", out_dir)
        elif script_key == "local_filter":
            rc, _ = run_readonly(script_file, tc_in / "app.log",  out_dir)
        elif script_key in MUTATING:
            rc, _ = run_mutating(script_file, tc_in, out_dir)
        else:
            return "unknown script"

        if rc == -1:  return "timeout"
        if rc != 0:   return "crash"

        for exp_file in sorted(expected_dir.iterdir()):
            got_file = out_dir / exp_file.name
            if not got_file.exists():
                return "missing output file"
            expected_text = normalize_output(script_key, exp_file.read_text())
            got_text      = normalize_output(script_key, got_file.read_text())
            if got_text != expected_text:
                return "output mismatch"

        return "PASS"

    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


# ─────────────────────────────────────────────────────────────────────────────
# Per-script grading
# ─────────────────────────────────────────────────────────────────────────────

def grade_script(script_key: str, q1_dir: Path, tc_base: Path) -> dict:
    """
    Returns a dict with:
        marks, max, tool_issues, tc_results, n_pass
    """
    max_marks   = MAX_MARKS[script_key]
    script_file = q1_dir / f"{script_key}.sh"

    if not script_file.exists():
        return dict(marks=0.0, max=max_marks,
                    tool_issues=["missing script"],
                    tc_results={tc: "missing script" for tc in TCS},
                    n_pass=0)

    tool_issues = check_tools(script_file, script_key)

    tc_results: dict[str, str] = {}
    for tc in TCS:
        tc_results[tc] = grade_tc(script_key, tc, script_file,
                                  tc_base / script_key)

    n_pass = sum(1 for r in tc_results.values() if r == "PASS")

    # weighted mark
    raw = max_marks * sum(
        TC_WEIGHTS[script_key][tc]
        for tc, r in tc_results.items()
        if r == "PASS"
    )

    # missing required tool → zero the whole script
    if any("missing required" in i for i in tool_issues):
        raw = 0.0

    # forbidden tool(s) → deduct per distinct tool
    n_forbidden = sum(1 for i in tool_issues if "forbidden" in i)
    raw = max(0.0, raw - n_forbidden * FORBIDDEN_PENALTY)

    return dict(
        marks      = round(raw, 2),
        max        = max_marks,
        tool_issues= tool_issues,
        tc_results = tc_results,
        n_pass     = n_pass,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Short comment builder  (CSV column — must be concise)
# ─────────────────────────────────────────────────────────────────────────────

def build_comment(result: dict) -> str:
    """
    Returns a short string describing deductions, or "" if full marks.
    Rules:
    - List each distinct issue once (tool problems first, then output issues).
    - Never mention individual test-case names.
    - Deduplicate repeated failure reasons across test cases.
    """
    parts: list[str] = list(result["tool_issues"])   # e.g. "uses python (forbidden)"

    # Unique output-level failure reasons, in order of first occurrence,
    # excluding PASS and any already described by a tool issue.
    seen: set[str] = set()
    for reason in result["tc_results"].values():
        if reason not in ("PASS", "missing script") and reason not in seen:
            seen.add(reason)
            parts.append(reason)

    return "; ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Grade one student
# ─────────────────────────────────────────────────────────────────────────────

def grade_student(student_id: str, student_dir: Path,
                  tc_base: Path, detail_path: Path) -> dict:

    q1_dir = student_dir / "q1"
    results: dict[str, dict] = {}
    for key in SCRIPTS:
        results[key] = grade_script(key, q1_dir, tc_base)

    total     = round(sum(r["marks"] for r in results.values()), 2)
    max_total = sum(r["max"]   for r in results.values())

    # CSV comments: only scripts with deductions, very short
    comment_parts = []
    for key, r in results.items():
        c = build_comment(r)
        if c:
            comment_parts.append(f"{key}: {c}")
    comments = " | ".join(comment_parts) if comment_parts else "all correct"

    # ── per-student detail file (verbose, for instructor review) ──
    with open(detail_path, "w") as fh:
        fh.write(f"Student : {student_id}\n")
        fh.write("=" * 52 + "\n")
        for key, r in results.items():
            fh.write(f"\n{key}.sh   [{r['marks']:.2f} / {r['max']}]\n")
            for issue in r["tool_issues"]:
                fh.write(f"  ! {issue}\n")
            for tc, outcome in r["tc_results"].items():
                mark = "✓" if outcome == "PASS" else "✗"
                fh.write(f"  {mark} {tc}: {outcome}\n")
            c = build_comment(r)
            if c:
                fh.write(f"  → deducted: {c}\n")
        fh.write("\n" + "=" * 52 + "\n")
        fh.write(f"TOTAL   : {total:.2f} / {max_total}\n")

    return {
        "id":          student_id,
        "total_marks": total,
        "max_marks":   max_total,
        **{key: r["marks"] for key, r in results.items()},
        "comments":    comments,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Grade Q1 bash/sed/awk submissions")
    parser.add_argument("--submissions", default="final_submissions",
                        help="Directory containing one sub-folder per student")
    parser.add_argument("--testcases",   default="testcases",
                        help="Directory containing testcase fixtures")
    parser.add_argument("--output",      default="grader_output",
                        help="Directory for grades.csv and per-student logs")
    args = parser.parse_args()

    subs_dir = Path(args.submissions).resolve()
    tc_dir   = Path(args.testcases).resolve()
    out_dir  = Path(args.output).resolve()

    if not subs_dir.exists():
        sys.exit(f"ERROR: submissions dir not found: {subs_dir}")
    if not tc_dir.exists():
        sys.exit(f"ERROR: testcases dir not found: {tc_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)
    per_student_dir = out_dir / "per_student"
    per_student_dir.mkdir(exist_ok=True)

    csv_path   = out_dir / "grades.csv"
    fieldnames = ["id", "total_marks", "max_marks"] + SCRIPTS + ["comments"]

    rows: list[dict] = []
    student_dirs = sorted(p for p in subs_dir.iterdir() if p.is_dir())

    for student_dir in student_dirs:
        sid = student_dir.name
        if not (student_dir / "q1").exists():
            print(f"  SKIP  {sid} — no q1/ directory")
            continue

        print(f"▶ {sid} ...", end="", flush=True)
        row = grade_student(
            sid, student_dir, tc_dir,
            detail_path=per_student_dir / f"{sid}.txt",
        )
        rows.append(row)
        print(f"  {row['total_marks']} / {row['max_marks']}")

    with open(csv_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone. Graded {len(rows)} student(s).")
    print(f"CSV    → {csv_path}")
    print(f"Logs   → {per_student_dir}/")


if __name__ == "__main__":
    main()

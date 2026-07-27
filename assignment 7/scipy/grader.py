#!/usr/bin/env python3
"""
grader.py

End-to-end autograder for Question 2 (Asteroid Defense System / Aegis
Interceptor), CSO606.

Expected submissions layout:

    submissions/
        <EO_ID>/
            q2/
                projectile.py
        <EO_ID>/
            q2/
                projectile.py
        ...

Usage:
    python3 generate_tests.py            # build tests/ once (or reuse existing)
    python3 grader.py                    # grade everything in submissions/

Outputs:
    results.csv          -- id, marks, comment  (one row per submission)
    logs/<EO_ID>.log      -- full per-test breakdown for that student

Run `python3 grader.py --help` for options.
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
import traceback

# --------------------------------------------------------------------------
# Marking scheme (tune here)
# --------------------------------------------------------------------------
TIME_TOL_FULL = 1e-3        # abs(time_diff) <= this -> full credit for the test
TIME_TOL_PARTIAL = 1.0      # abs(time_diff) <= this -> partial credit
PARTIAL_CREDIT_FRACTION = 0.6   # awarded when decision right, time within TIME_TOL_PARTIAL
MINIMAL_CREDIT_FRACTION = 0.2   # awarded when decision right, time way off
DEFAULT_TIMEOUT = 15        # seconds, per test case (overridden by meta.json's timeout_s)
MARKS_ROUND_NDIGITS = 2

HIT_RE = re.compile(r"^\s*HIT\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*$", re.IGNORECASE)
MISS_RE = re.compile(r"^\s*MISS\s*$", re.IGNORECASE)


def load_tests(tests_dir):
    """Returns a list of dicts: {name, category, description, weight,
    timeout_s, expected, input_text}, sorted by name."""
    manifest_path = os.path.join(tests_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        sys.exit(
            f"error: {manifest_path} not found. Run `python3 generate_tests.py` first."
        )
    with open(manifest_path) as f:
        manifest = json.load(f)

    cases = []
    for meta in manifest["cases"]:
        case_dir = os.path.join(tests_dir, meta["name"])
        with open(os.path.join(case_dir, "input.txt")) as f:
            input_text = f.read()
        case = dict(meta)
        case["input_text"] = input_text
        cases.append(case)
    cases.sort(key=lambda c: c["name"])
    return cases, manifest["total_weight"]


def parse_output(raw_stdout):
    """Returns (kind, value, note) where kind in {'HIT','MISS','FORMAT_ERROR'}.
    Looks at the last non-blank line, to tolerate stray blank lines/trailing
    newlines without being lenient about genuinely wrong output."""
    lines = [ln for ln in raw_stdout.splitlines() if ln.strip() != ""]
    note = None
    if len(lines) == 0:
        return "FORMAT_ERROR", None, "no output produced"
    if len(lines) > 1:
        note = f"{len(lines)} non-blank output lines; graded the last one: {lines[-1]!r}"
    last = lines[-1]

    m = HIT_RE.match(last)
    if m:
        if not last.strip().startswith("HIT"):
            note = (note + "; " if note else "") + "keyword case did not match 'HIT' exactly (graded leniently)"
        return "HIT", float(m.group(1)), note
    m = MISS_RE.match(last)
    if m:
        if last.strip() != "MISS":
            note = (note + "; " if note else "") + "keyword case did not match 'MISS' exactly (graded leniently)"
        return "MISS", None, note
    return "FORMAT_ERROR", None, f"unparseable output: {last!r}"


def run_one_test(script_path, test, timeout_scale):
    """Runs the student's script against a single test case. Returns a dict
    describing what happened, always including 'marks_awarded' (0..weight)."""
    weight = test["weight"]
    timeout_s = test.get("timeout_s", DEFAULT_TIMEOUT) * timeout_scale

    result = {
        "test": test["name"],
        "category": test["category"],
        "description": test["description"],
        "weight": weight,
        "expected": test["expected"],
    }

    start = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, os.path.basename(script_path)],
            input=test["input_text"],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=os.path.dirname(script_path),
        )
    except subprocess.TimeoutExpired:
        result.update(status="TIMEOUT", marks_awarded=0.0,
                       detail=f"exceeded {timeout_s:.1f}s timeout")
        return result
    except Exception as e:
        result.update(status="HARNESS_ERROR", marks_awarded=0.0,
                       detail=f"grader failed to launch script: {e!r}")
        return result
    elapsed = time.time() - start

    if proc.returncode != 0:
        stderr_tail = proc.stderr.strip()[-2000:]
        result.update(status="RUNTIME_ERROR", marks_awarded=0.0,
                       detail=f"exit code {proc.returncode}", stderr=stderr_tail,
                       elapsed_s=round(elapsed, 3))
        return result

    kind, value, note = parse_output(proc.stdout)
    result["actual_raw"] = proc.stdout.strip()[-500:]
    result["elapsed_s"] = round(elapsed, 3)
    if note:
        result["note"] = note
    if proc.stderr.strip():
        result["stderr"] = proc.stderr.strip()[-1000:]

    if kind == "FORMAT_ERROR":
        result.update(status="FORMAT_ERROR", marks_awarded=0.0, detail=note)
        return result

    expected_kind = "HIT" if test["expected"].startswith("HIT") else "MISS"

    if kind != expected_kind:
        result.update(status="WRONG_DECISION", marks_awarded=0.0,
                       detail=f"expected {expected_kind}, got {kind}")
        return result

    if expected_kind == "MISS":
        result.update(status="CORRECT", marks_awarded=float(weight))
        return result

    # Both HIT: compare times.
    expected_time = float(test["expected"].split()[1])
    diff = abs(value - expected_time)
    result["expected_time"] = expected_time
    result["actual_time"] = value
    result["time_diff"] = round(diff, 6)

    if diff <= TIME_TOL_FULL:
        result.update(status="CORRECT", marks_awarded=float(weight))
    elif diff <= TIME_TOL_PARTIAL:
        result.update(status="HIT_IMPRECISE", marks_awarded=round(weight * PARTIAL_CREDIT_FRACTION, 4))
    else:
        result.update(status="HIT_WRONG_TIME", marks_awarded=round(weight * MINIMAL_CREDIT_FRACTION, 4))
    return result


def grade_submission(eo_id, script_path, tests, timeout_scale):
    test_results = []
    for test in tests:
        test_results.append(run_one_test(script_path, test, timeout_scale))
    total = sum(r["marks_awarded"] for r in test_results)
    return test_results, total


def summarize_comment(eo_id, total_weight, marks, test_results, missing=False, missing_reason=""):
    if missing:
        return f"No submission found for q2 ({missing_reason})."

    n = len(test_results)
    n_correct = sum(1 for r in test_results if r["status"] == "CORRECT")
    n_wrong = sum(1 for r in test_results if r["status"] == "WRONG_DECISION")
    n_crash = sum(1 for r in test_results if r["status"] in ("RUNTIME_ERROR", "HARNESS_ERROR"))
    n_timeout = sum(1 for r in test_results if r["status"] == "TIMEOUT")
    n_format = sum(1 for r in test_results if r["status"] == "FORMAT_ERROR")
    n_imprecise = sum(1 for r in test_results if r["status"] in ("HIT_IMPRECISE", "HIT_WRONG_TIME"))

    if n_correct == n:
        return f"All {n} test cases passed ({marks:.1f}/{total_weight})."

    parts = [f"{n_correct}/{n} test cases fully correct."]
    if n_crash:
        # surface the most common-looking error for a quick hint
        sample = next((r for r in test_results if r["status"] in ("RUNTIME_ERROR", "HARNESS_ERROR")), None)
        hint = ""
        if sample and sample.get("stderr"):
            last_line = sample["stderr"].strip().splitlines()[-1] if sample["stderr"].strip() else ""
            hint = f" (e.g. {last_line[:120]})" if last_line else ""
        parts.append(f"Crashed on {n_crash}{hint}.")
    if n_timeout:
        parts.append(f"Timed out on {n_timeout}.")
    if n_format:
        parts.append(f"Bad output format on {n_format}.")
    if n_wrong:
        parts.append(f"Wrong HIT/MISS decision on {n_wrong}.")
    if n_imprecise:
        parts.append(f"HIT decision right but imprecise timing on {n_imprecise}.")
    return " ".join(parts)


def write_log(log_path, eo_id, script_path, tests_dir, total_weight, marks, test_results, missing=False, missing_reason=""):
    with open(log_path, "w") as f:
        f.write(f"Autograder log for {eo_id}\n")
        f.write(f"Script: {script_path}\n")
        f.write(f"Tests directory: {tests_dir}\n")
        f.write("=" * 78 + "\n\n")

        if missing:
            f.write(f"SUBMISSION MISSING: {missing_reason}\n")
            f.write(f"\nTOTAL MARKS: 0 / {total_weight}\n")
            return

        for r in test_results:
            f.write(f"[{r['status']:>15s}] {r['test']}  (weight={r['weight']}, "
                     f"awarded={r['marks_awarded']:.2f})\n")
            f.write(f"    category   : {r['category']}\n")
            f.write(f"    description: {r['description']}\n")
            f.write(f"    expected   : {r['expected']}\n")
            if "actual_raw" in r:
                f.write(f"    actual     : {r['actual_raw']!r}\n")
            if "elapsed_s" in r:
                f.write(f"    elapsed    : {r['elapsed_s']}s\n")
            if "time_diff" in r:
                f.write(f"    time diff  : {r['time_diff']}s (tol full={TIME_TOL_FULL}, partial={TIME_TOL_PARTIAL})\n")
            if r.get("detail"):
                f.write(f"    detail     : {r['detail']}\n")
            if r.get("note"):
                f.write(f"    note       : {r['note']}\n")
            if r.get("stderr"):
                f.write(f"    stderr (tail):\n")
                for line in r["stderr"].splitlines()[-30:]:
                    f.write(f"        {line}\n")
            f.write("\n")

        f.write("=" * 78 + "\n")
        f.write(f"TOTAL MARKS: {marks:.2f} / {total_weight}\n")


def find_submissions(submissions_dir, qdir_name="q2", script_name="projectile.py"):
    """Yields (eo_id, script_path_or_None, missing_reason_or_None)."""
    if not os.path.isdir(submissions_dir):
        sys.exit(f"error: submissions directory not found: {submissions_dir}")
    for eo_id in sorted(os.listdir(submissions_dir)):
        eo_path = os.path.join(submissions_dir, eo_id)
        if not os.path.isdir(eo_path):
            continue
        q_dir = os.path.join(eo_path, qdir_name)
        script_path = os.path.join(q_dir, script_name)
        if not os.path.isdir(q_dir):
            yield eo_id, None, f"'{qdir_name}/' directory not found"
        elif not os.path.isfile(script_path):
            yield eo_id, None, f"'{qdir_name}/{script_name}' not found"
        else:
            yield eo_id, script_path, None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--submissions-dir", default="../final_submissions")
    ap.add_argument("--tests-dir", default="tests")
    ap.add_argument("--output-csv", default="results.csv")
    ap.add_argument("--logs-dir", default="logs")
    ap.add_argument("--timeout-scale", type=float, default=1.0,
                     help="multiply every test's timeout by this factor (e.g. 2.0 on a slow grading machine)")
    ap.add_argument("--qdir-name", default="q2")
    ap.add_argument("--script-name", default="projectile.py")
    args = ap.parse_args()

    tests, total_weight = load_tests(args.tests_dir)
    os.makedirs(args.logs_dir, exist_ok=True)

    submissions = list(find_submissions(args.submissions_dir, args.qdir_name, args.script_name))
    if not submissions:
        sys.exit(f"error: no submission directories found under {args.submissions_dir}")

    rows = []
    print(f"Grading {len(submissions)} submission(s) against {len(tests)} test cases "
          f"(total weight = {total_weight})...\n")

    for i, (eo_id, script_path, missing_reason) in enumerate(submissions, 1):
        log_path = os.path.join(args.logs_dir, f"{eo_id}.log")

        if script_path is None:
            marks = 0.0
            comment = summarize_comment(eo_id, total_weight, marks, [], missing=True, missing_reason=missing_reason)
            write_log(log_path, eo_id, "(none)", args.tests_dir, total_weight, marks, [],
                      missing=True, missing_reason=missing_reason)
            print(f"[{i}/{len(submissions)}] {eo_id}: 0/{total_weight}  ({missing_reason})")
            rows.append({"id": eo_id, "marks": round(marks, MARKS_ROUND_NDIGITS), "comment": comment})
            continue

        try:
            test_results, marks = grade_submission(eo_id, script_path, tests, args.timeout_scale)
        except Exception:
            # Should not normally happen (per-test errors are already caught),
            # but never let one bad submission crash the whole grading run.
            tb = traceback.format_exc()
            marks = 0.0
            comment = "Grader-internal error while grading this submission; see log."
            write_log(log_path, eo_id, script_path, args.tests_dir, total_weight, marks, [],
                      missing=True, missing_reason=f"internal grader error:\n{tb}")
            print(f"[{i}/{len(submissions)}] {eo_id}: 0/{total_weight}  (GRADER ERROR, see log)")
            rows.append({"id": eo_id, "marks": round(marks, MARKS_ROUND_NDIGITS), "comment": comment})
            continue

        comment = summarize_comment(eo_id, total_weight, marks, test_results)
        write_log(log_path, eo_id, script_path, args.tests_dir, total_weight, marks, test_results)
        print(f"[{i}/{len(submissions)}] {eo_id}: {marks:.2f}/{total_weight}  ({comment})")
        rows.append({"id": eo_id, "marks": round(marks, MARKS_ROUND_NDIGITS), "comment": comment})

    with open(args.output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "marks", "comment"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {args.output_csv} ({len(rows)} rows) and per-student logs to {args.logs_dir}/")


if __name__ == "__main__":
    main()

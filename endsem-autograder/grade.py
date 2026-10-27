"""
CSO606 NumPy/Pandas/SciPy autograder.

Usage:
    python3 grade.py --submissions-dir submissions --output results.csv --logs-dir logs

Expected layout (one folder per student, matching the assignment's own
resources/ structure):

    submissions/
      <student_id>/
        NumPy/np_submission.py
        Pandas/pd_submission.py
        SciPy/sc_submission.py

A student folder missing a module file just gets 0 for that module —
grading continues for the rest.

For each module file this script:
  1. Statically checks the source for explicit for/while loops (AST).
  2. Calls task1..taskN directly (no runner) against a fixed set of test
     cases per task, in an isolated, timed subprocess (sandbox.py).
  3. Compares each result against the reference solution (compare.py).
  4. Awards marks per task proportional to test cases passed, then applies
     the loop-violation multiplier if step 1 found a violation.

Produces:
  - results.csv:  student_id, <module>_marks per module, total, loop_violations, comment
  - logs/<student_id>.log: full detail — every test case, pass/fail, timing, errors
"""

import argparse
import csv
from pathlib import Path

from config import MARKS, SUBMISSION_FILENAMES, LOOP_VIOLATION_MARKS_MULTIPLIER
from test_data import build_all_cases
from reference_solutions import ALL_REFS
from compare import COMPARATORS
from static_checks import check_no_loops
from sandbox import run_task

MODULES = ["NumPy", "Pandas", "SciPy"]


def grade_module_file(module_name, submission_path, cases_by_task, log_lines):
    """
    Returns (marks_awarded, max_marks, loop_violation: bool).
    Appends detailed lines to log_lines as it goes.
    """
    max_marks = sum(MARKS[module_name].values())

    if not submission_path.exists():
        log_lines.append(f"  [MISSING] {submission_path.name} not found — 0/{max_marks}")
        return 0.0, max_marks, False

    source = submission_path.read_text()
    ok, violations, parse_error = check_no_loops(source)

    if parse_error:
        log_lines.append(f"  [PARSE ERROR] {parse_error} — 0/{max_marks}")
        return 0.0, max_marks, False

    loop_violation = not ok
    if loop_violation:
        loc = ", ".join(f"line {ln} ({kind})" for ln, kind in violations)
        log_lines.append(f"  [LOOP VIOLATION] explicit loop(s) found: {loc}")

    refs = ALL_REFS[module_name]
    comparators = COMPARATORS[module_name]
    total_awarded = 0.0

    for task_name, task_marks in MARKS[module_name].items():
        cases = cases_by_task[task_name]
        n_cases = len(cases)
        marks_per_case = task_marks / n_cases
        task_awarded = 0.0

        for case in cases:
            expected = refs[task_name](*case["args"])
            outcome = run_task(str(submission_path), task_name, case["args"], case["timeout"])

            if outcome["status"] == "ok":
                passed, detail = comparators[task_name](outcome["result"], expected)
                elapsed = outcome["elapsed"]
                if passed:
                    task_awarded += marks_per_case
                    log_lines.append(
                        f"  [PASS] {task_name} / {case['name']}  ({elapsed:.3f}s)"
                    )
                else:
                    log_lines.append(
                        f"  [FAIL] {task_name} / {case['name']}  ({elapsed:.3f}s) — {detail}"
                    )
            elif outcome["status"] == "timeout":
                log_lines.append(
                    f"  [TIMEOUT] {task_name} / {case['name']} — {outcome['message']}"
                )
            else:  # error
                log_lines.append(
                    f"  [ERROR] {task_name} / {case['name']} — {outcome['message']}"
                )

        log_lines.append(f"  -> {task_name}: {task_awarded:.2f}/{task_marks}")
        total_awarded += task_awarded

    if loop_violation:
        penalized = total_awarded * LOOP_VIOLATION_MARKS_MULTIPLIER
        log_lines.append(
            f"  [PENALTY] loop violation: {total_awarded:.2f} -> {penalized:.2f} "
            f"(x{LOOP_VIOLATION_MARKS_MULTIPLIER})"
        )
        total_awarded = penalized

    return total_awarded, max_marks, loop_violation


def grade_student(student_id, student_dir, all_cases):
    log_lines = [f"=== {student_id} ==="]
    module_marks = {}
    any_loop_violation = False

    for module_name in MODULES:
        filename = SUBMISSION_FILENAMES[module_name]
        submission_path = student_dir / module_name / filename
        log_lines.append(f"-- {module_name} ({filename}) --")

        awarded, max_marks, loop_violation = grade_module_file(
            module_name, submission_path, all_cases[module_name], log_lines
        )
        module_marks[module_name] = awarded
        any_loop_violation = any_loop_violation or loop_violation

    total = sum(module_marks.values())
    log_lines.append(f"TOTAL: {total:.2f}")
    return module_marks, total, any_loop_violation, "\n".join(log_lines)


def main():
    parser = argparse.ArgumentParser(description="CSO606 NumPy/Pandas/SciPy autograder")
    parser.add_argument("--submissions-dir", default="submissions",
                         help="Directory containing one subfolder per student")
    parser.add_argument("--output", default="results.csv", help="Output CSV path")
    parser.add_argument("--logs-dir", default="logs", help="Per-student detailed log directory")
    args = parser.parse_args()

    submissions_dir = Path(args.submissions_dir)
    logs_dir = Path(args.logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    if not submissions_dir.exists():
        raise SystemExit(f"Submissions directory not found: {submissions_dir}")

    student_dirs = sorted(p for p in submissions_dir.iterdir() if p.is_dir())
    if not student_dirs:
        raise SystemExit(f"No student subfolders found in {submissions_dir}")

    all_cases = build_all_cases()

    rows = []
    for student_dir in student_dirs:
        student_id = student_dir.name
        module_marks, total, loop_violation, log_text = grade_student(
            student_id, student_dir, all_cases
        )
        (logs_dir / f"{student_id}.log").write_text(log_text)

        comment = "loop violation(s) found — see log" if loop_violation else ""
        rows.append({
            "student_id": student_id,
            **{f"{m.lower()}_marks": round(module_marks[m], 2) for m in MODULES},
            "total_marks": round(total, 2),
            "loop_violation": loop_violation,
            "comment": comment,
        })
        print(f"{student_id}: {round(total, 2)}"
              f"{'  [LOOP VIOLATION]' if loop_violation else ''}")

    fieldnames = (["student_id"] + [f"{m.lower()}_marks" for m in MODULES]
                  + ["total_marks", "loop_violation", "comment"])
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {args.output}")
    print(f"Per-student logs in {logs_dir}/")


if __name__ == "__main__":
    main()

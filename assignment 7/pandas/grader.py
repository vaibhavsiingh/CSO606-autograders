#!/usr/bin/env python3
"""
Autograder for CSO606 Q1: The Lost Research Archive (40 marks).

Usage:
    python3 grader.py [--submissions submissions] [--out results.csv] [--logs logs]

Expected submission layout:
    submissions/<EO_ID>/q1/q1_t1.py
    submissions/<EO_ID>/q1/q1_t2.py
    submissions/<EO_ID>/q1/q1_t3.py
    submissions/<EO_ID>/q1/q1_t4.py

For each student script, the grader:
  1. Copies the golden input CSV(s) next to the script in an isolated temp dir.
  2. Runs the script with `python3 <script>` (cwd = temp dir), with a timeout.
  3. Loads the produced output CSV (if any) and compares it against the golden
     output using tolerant, partial-credit comparison logic.
  4. Records marks + a short comment, and a full detailed log per student.

Output:
  - results.csv   columns: id, marks, comment
  - logs/<id>.log detailed per-task breakdown, stdout/stderr, tracebacks
"""
import argparse
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

TIMEOUT_SECONDS = 60
FLOAT_RTOL = 1e-2
FLOAT_ATOL = 1e-2

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"

# ---- marks scheme (sums to 40) ----
T1_PARTA_MARKS = 6.0   # passenger_count, survivor_count, survival_pct, avg_age, median_fare, age_std
T1_PARTB_MARKS = 3.0   # survival_rank
T1_PARTC_MARKS = 5.0   # mean_rolling_survival, max_rolling_survival
T2_MARKS = 8.0
T3_MARKS = 8.0
T4_MARKS = 10.0
TOTAL_MARKS = T1_PARTA_MARKS + T1_PARTB_MARKS + T1_PARTC_MARKS + T2_MARKS + T3_MARKS + T4_MARKS
assert abs(TOTAL_MARKS - 40.0) < 1e-9


class TaskResult:
    def __init__(self, name, max_marks):
        self.name = name
        self.max_marks = max_marks
        self.marks = 0.0
        self.notes = []  # list of short strings for the log
        self.short_issue = None  # short summary for the CSV comment, if this task lost marks

    def award(self, marks, note):
        self.marks = max(0.0, min(self.max_marks, marks))
        self.notes.append(note)

    def fail(self, short_issue, note=None):
        self.marks = 0.0
        self.short_issue = short_issue
        self.notes.append(note or short_issue)


def run_script(script_path: Path, workdir: Path):
    """Run a student script with cwd=workdir. Returns (ok, stdout, stderr, error_summary)."""
    if not script_path.exists():
        return False, "", "", f"{script_path.name} not submitted"
    try:
        proc = subprocess.run(
            [sys.executable, script_path.name],
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return False, "", "", f"timed out after {TIMEOUT_SECONDS}s"
    except Exception as e:
        return False, "", "", f"failed to launch subprocess: {e}"

    if proc.returncode != 0:
        # keep last part of stderr (tracebacks can be long)
        err_tail = proc.stderr.strip().splitlines()
        err_summary = err_tail[-1] if err_tail else f"exited with code {proc.returncode}"
        return False, proc.stdout, proc.stderr, err_summary
    return True, proc.stdout, proc.stderr, None


def format_run_error(err: str) -> str:
    if err.endswith("not submitted") or "timed out" in err:
        return err
    return f"script crashed ({err})"


def safe_read_csv(path: Path):
    if not path.exists():
        return None, "output file not produced"
    try:
        df = pd.read_csv(path)
        return df, None
    except Exception as e:
        return None, f"output CSV could not be parsed ({e})"


def col_match_fraction(student_series, golden_series):
    """Fraction of entries that match within tolerance (numeric, NaN-aware) or exactly (non-numeric)."""
    if len(golden_series) == 0:
        return 1.0
    n = len(golden_series)
    matches = 0
    s_vals = student_series.values
    g_vals = golden_series.values
    for sv, gv in zip(s_vals, g_vals):
        try:
            sv_is_nan = pd.isna(sv)
            gv_is_nan = pd.isna(gv)
        except Exception:
            sv_is_nan = gv_is_nan = False
        if sv_is_nan and gv_is_nan:
            matches += 1
            continue
        if sv_is_nan or gv_is_nan:
            continue
        try:
            if np.isclose(float(sv), float(gv), rtol=FLOAT_RTOL, atol=FLOAT_ATOL):
                matches += 1
        except (ValueError, TypeError):
            if str(sv).strip().lower() == str(gv).strip().lower():
                matches += 1
    return matches / n


# ---------------------------------------------------------------------------
# Task 1: Passenger Archive Analysis
# ---------------------------------------------------------------------------
def grade_t1(student_dir: Path, log):
    partA = TaskResult("Task1-PartA", T1_PARTA_MARKS)
    partB = TaskResult("Task1-PartB", T1_PARTB_MARKS)
    partC = TaskResult("Task1-PartC", T1_PARTC_MARKS)

    script = student_dir / "q1_t1.py"
    workdir = student_dir
    shutil.copy(DATA_DIR / "q1_t1_input.csv", workdir / "q1_t1_input.csv")
    out_path = workdir / "q1_t1_output.csv"
    if out_path.exists():
        out_path.unlink()

    ok, stdout, stderr, err = run_script(script, workdir)
    log.append(f"[Task1] run ok={ok} stdout_len={len(stdout)}")
    if stdout.strip():
        log.append(f"[Task1] stdout tail: {stdout.strip()[-500:]}")
    if not ok:
        msg = format_run_error(err)
        partA.fail(msg, f"[Task1] {msg}\n[Task1] stderr tail: {stderr.strip()[-1000:]}")
        partB.fail(msg)
        partC.fail(msg)
        return partA, partB, partC

    student_df, read_err = safe_read_csv(out_path)
    if student_df is None:
        partA.fail(read_err, f"[Task1] {read_err}")
        partB.fail(read_err)
        partC.fail(read_err)
        return partA, partB, partC

    golden = pd.read_csv(DATA_DIR / "q1_t1_golden.csv")

    required_cols = [
        'pclass', 'sex', 'passenger_count', 'survivor_count', 'survival_pct',
        'avg_age', 'median_fare', 'age_std', 'survival_rank',
        'mean_rolling_survival', 'max_rolling_survival'
    ]
    missing = [c for c in required_cols if c not in student_df.columns]
    if missing:
        short_msg = f"output missing {len(missing)} required column(s)"
        full_msg = f"missing columns: {missing}"
        partA.fail(short_msg, f"[Task1] {full_msg}")
        partB.fail(short_msg)
        partC.fail(short_msg)
        return partA, partB, partC

    # normalize sex casing/whitespace, align keys
    student_df = student_df.copy()
    student_df['sex'] = student_df['sex'].astype(str).str.strip().str.lower()
    student_df['pclass'] = pd.to_numeric(student_df['pclass'], errors='coerce')

    try:
        merged = golden.merge(
            student_df, on=['pclass', 'sex'], how='left', suffixes=('_gold', '_stu')
        )
    except Exception as e:
        msg = f"could not align rows on (pclass, sex): {e}"
        partA.fail(msg, f"[Task1] {msg}")
        partB.fail(msg)
        partC.fail(msg)
        return partA, partB, partC

    if merged.shape[0] != golden.shape[0] or merged['passenger_count_stu'].isna().any():
        log.append(f"[Task1] WARNING: not all (pclass, sex) groups from golden found in student output "
                    f"({merged['passenger_count_stu'].notna().sum()}/{golden.shape[0]} groups present)")

    partA_cols = ['passenger_count', 'survivor_count', 'survival_pct', 'avg_age', 'median_fare', 'age_std']
    per_col_marks = T1_PARTA_MARKS / len(partA_cols)
    total_a = 0.0
    for c in partA_cols:
        frac = col_match_fraction(merged[f'{c}_stu'], merged[f'{c}_gold'])
        earned = per_col_marks * frac
        total_a += earned
        log.append(f"[Task1-PartA] {c}: {frac*100:.0f}% groups match -> {earned:.2f}/{per_col_marks:.2f}")
    partA.award(total_a, f"Part A total: {total_a:.2f}/{T1_PARTA_MARKS}")
    if total_a < T1_PARTA_MARKS - 1e-6:
        partA.short_issue = "warmup stats partially incorrect"

    frac_rank = col_match_fraction(merged['survival_rank_stu'], merged['survival_rank_gold'])
    partB.award(T1_PARTB_MARKS * frac_rank, f"[Task1-PartB] survival_rank: {frac_rank*100:.0f}% match")
    if frac_rank < 1.0:
        partB.short_issue = "survival_rank incorrect"

    partC_cols = ['mean_rolling_survival', 'max_rolling_survival']
    per_col_marks_c = T1_PARTC_MARKS / len(partC_cols)
    total_c = 0.0
    for c in partC_cols:
        frac = col_match_fraction(merged[f'{c}_stu'], merged[f'{c}_gold'])
        earned = per_col_marks_c * frac
        total_c += earned
        log.append(f"[Task1-PartC] {c}: {frac*100:.0f}% groups match -> {earned:.2f}/{per_col_marks_c:.2f}")
    partC.award(total_c, f"Part C total: {total_c:.2f}/{T1_PARTC_MARKS}")
    if total_c < T1_PARTC_MARKS - 1e-6:
        partC.short_issue = "rolling survival trend incorrect"

    return partA, partB, partC


# ---------------------------------------------------------------------------
# Task 2: Signal Recovery Puzzle
# ---------------------------------------------------------------------------
def grade_t2(student_dir: Path, log):
    res = TaskResult("Task2", T2_MARKS)
    script = student_dir / "q1_t2.py"
    workdir = student_dir
    shutil.copy(DATA_DIR / "q1_t2_input.csv", workdir / "q1_t2_input.csv")
    out_path = workdir / "q1_t2_output.csv"
    if out_path.exists():
        out_path.unlink()

    ok, stdout, stderr, err = run_script(script, workdir)
    log.append(f"[Task2] run ok={ok}")
    if not ok:
        msg = format_run_error(err)
        res.fail(msg, f"[Task2] {msg}\n[Task2] stderr tail: {stderr.strip()[-1000:]}")
        return res

    student_df, read_err = safe_read_csv(out_path)
    if student_df is None:
        res.fail(read_err, f"[Task2] {read_err}")
        return res

    if 'since_reset' not in student_df.columns:
        res.fail("missing 'since_reset' column", "[Task2] missing 'since_reset' column")
        return res

    golden = pd.read_csv(DATA_DIR / "q1_t2_golden.csv")
    if len(student_df) != len(golden):
        res.fail(
            f"row count mismatch (expected {len(golden)}, got {len(student_df)})",
            f"[Task2] row count mismatch: expected {len(golden)}, got {len(student_df)}"
        )
        return res

    # align by timestamp if present, else by position
    try:
        if 'timestamp' in student_df.columns and 'timestamp' in golden.columns:
            merged = golden.merge(student_df[['timestamp', 'since_reset']], on='timestamp',
                                   how='left', suffixes=('_gold', '_stu'))
            stu_col, gold_col = 'since_reset_stu', 'since_reset_gold'
        else:
            merged = golden.copy()
            merged['since_reset_stu'] = student_df['since_reset'].values
            stu_col, gold_col = 'since_reset_stu', 'since_reset'
        frac = col_match_fraction(merged[stu_col], merged[gold_col])
    except Exception as e:
        res.fail(f"comparison error: {e}", f"[Task2] comparison error: {e}\n{traceback.format_exc()}")
        return res

    marks = T2_MARKS * frac
    res.award(marks, f"[Task2] since_reset match: {frac*100:.1f}% -> {marks:.2f}/{T2_MARKS}")
    if frac < 1.0:
        res.short_issue = f"since_reset only {frac*100:.0f}% correct"
    return res


# ---------------------------------------------------------------------------
# Task 3: Fragment Reconstruction Puzzle
# ---------------------------------------------------------------------------
def grade_t3(student_dir: Path, log):
    res = TaskResult("Task3", T3_MARKS)
    script = student_dir / "q1_t3.py"
    workdir = student_dir
    shutil.copy(DATA_DIR / "q1_t3_input.csv", workdir / "q1_t3_input.csv")
    out_path = workdir / "q1_t3_output.csv"
    if out_path.exists():
        out_path.unlink()

    ok, stdout, stderr, err = run_script(script, workdir)
    log.append(f"[Task3] run ok={ok}")
    if not ok:
        msg = format_run_error(err)
        res.fail(msg, f"[Task3] {msg}\n[Task3] stderr tail: {stderr.strip()[-1000:]}")
        return res

    student_df, read_err = safe_read_csv(out_path)
    if student_df is None:
        res.fail(read_err, f"[Task3] {read_err}")
        return res

    if 'smoothened_measurement' not in student_df.columns:
        res.fail("missing 'smoothened_measurement' column", "[Task3] missing 'smoothened_measurement' column")
        return res

    golden = pd.read_csv(DATA_DIR / "q1_t3_golden.csv")
    if len(student_df) != len(golden):
        res.fail(
            f"row count mismatch (expected {len(golden)}, got {len(student_df)})",
            f"[Task3] row count mismatch: expected {len(golden)}, got {len(student_df)}"
        )
        return res

    try:
        # rows must preserve original transmission order (grader assumes order preserved)
        merged = golden[['experiment', 'measurement', 'smoothened_measurement']].reset_index(drop=True).copy()
        merged['stu'] = student_df['smoothened_measurement'].reset_index(drop=True).values
        # sanity check alignment via experiment/measurement columns if present in student output
        alignment_ok = True
        if 'experiment' in student_df.columns:
            exp_match = (student_df['experiment'].reset_index(drop=True).astype(str).str.strip()
                         == merged['experiment'].astype(str).str.strip())
            alignment_ok = exp_match.mean() > 0.95
        if not alignment_ok:
            res.fail("row order does not match input order (rows appear reshuffled)",
                     "[Task3] row order mismatch vs input; grader requires original order preserved")
            return res
        frac = col_match_fraction(merged['stu'], merged['smoothened_measurement'])
    except Exception as e:
        res.fail(f"comparison error: {e}", f"[Task3] comparison error: {e}\n{traceback.format_exc()}")
        return res

    marks = T3_MARKS * frac
    res.award(marks, f"[Task3] smoothened_measurement match: {frac*100:.1f}% -> {marks:.2f}/{T3_MARKS}")
    if frac < 1.0:
        res.short_issue = f"smoothened_measurement only {frac*100:.0f}% correct"
    return res


# ---------------------------------------------------------------------------
# Task 4: Minefield Mapping System
# ---------------------------------------------------------------------------
def load_grid_flexibly(path: Path, expected_ys, expected_xs):
    """Try to parse a submitted grid CSV into a DataFrame indexed by y with columns=x."""
    raw = pd.read_csv(path)
    expected_ys = list(expected_ys)
    expected_xs = list(expected_xs)

    first_col = raw.columns[0]
    first_col_vals = pd.to_numeric(raw[first_col], errors='coerce')
    if set(first_col_vals.dropna().astype(int)) == set(expected_ys) and first_col_vals.notna().all():
        grid = raw.set_index(first_col)
        grid.index = grid.index.astype(int)
    else:
        # assume default RangeIndex was written (student used index=False or index matches order)
        grid = raw.copy()
        if len(grid) == len(expected_ys):
            grid.index = expected_ys
        else:
            raise ValueError(f"cannot determine y-index (rows={len(grid)}, expected={len(expected_ys)})")

    # try to coerce column headers to int x-values
    new_cols = []
    for c in grid.columns:
        try:
            new_cols.append(int(float(c)))
        except (ValueError, TypeError):
            new_cols.append(c)
    grid.columns = new_cols

    missing_x = [x for x in expected_xs if x not in grid.columns]
    if missing_x:
        if grid.shape[1] == len(expected_xs):
            # fall back to positional mapping
            grid.columns = expected_xs
        else:
            raise ValueError(f"cannot align x-columns; missing {missing_x[:5]}... "
                              f"(have {list(grid.columns)[:8]})")

    grid = grid.reindex(index=expected_ys, columns=expected_xs)
    return grid


def grade_t4(student_dir: Path, log):
    res = TaskResult("Task4", T4_MARKS)
    script = student_dir / "q1_t4.py"
    workdir = student_dir
    shutil.copy(DATA_DIR / "q1_t4_input.csv", workdir / "q1_t4_input.csv")
    out_path = workdir / "q1_t4_output.csv"
    if out_path.exists():
        out_path.unlink()

    ok, stdout, stderr, err = run_script(script, workdir)
    log.append(f"[Task4] run ok={ok}")
    if not ok:
        msg = format_run_error(err)
        res.fail(msg, f"[Task4] {msg}\n[Task4] stderr tail: {stderr.strip()[-1000:]}")
        return res

    if not out_path.exists():
        res.fail("output file not produced", "[Task4] output file not produced")
        return res

    golden = pd.read_csv(DATA_DIR / "q1_t4_golden.csv", index_col=0)
    golden.columns = [int(c) for c in golden.columns]
    expected_ys = list(golden.index)
    expected_xs = list(golden.columns)

    try:
        student_grid = load_grid_flexibly(out_path, expected_ys, expected_xs)
    except Exception as e:
        res.fail(f"output grid format unreadable ({e})",
                 f"[Task4] grid parse error: {e}\n{traceback.format_exc()}")
        return res

    total = golden.shape[0] * golden.shape[1]
    matches = 0
    for y in expected_ys:
        for x in expected_xs:
            gv = golden.loc[y, x]
            try:
                sv = student_grid.loc[y, x]
            except Exception:
                sv = np.nan
            g_nan, s_nan = pd.isna(gv), pd.isna(sv)
            if g_nan and s_nan:
                matches += 1
            elif not g_nan and not s_nan:
                try:
                    if np.isclose(float(gv), float(sv), rtol=FLOAT_RTOL, atol=FLOAT_ATOL):
                        matches += 1
                except (ValueError, TypeError):
                    pass
    frac = matches / total
    marks = T4_MARKS * frac
    res.award(marks, f"[Task4] grid cell match: {matches}/{total} ({frac*100:.1f}%) -> {marks:.2f}/{T4_MARKS}")
    if frac < 1.0:
        res.short_issue = f"hazard grid only {frac*100:.0f}% correct"
    return res


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def build_comment(task_results):
    """Short 1-2 sentence comment summarizing what went wrong (or praise if perfect).
    Groups Task1's three parts into a single entry so one crash doesn't repeat 3x
    and crowd out genuine issues in Tasks 2-4."""
    # group by top-level task (Task1-PartA/B/C -> "T1", Task2 -> "T2", ...)
    groups = {}
    order = []
    for t in task_results:
        top = t.name.split('-')[0].replace('Task', 'T')
        if top not in groups:
            groups[top] = []
            order.append(top)
        if t.short_issue:
            groups[top].append(t.short_issue)

    entries = []
    for top in order:
        issues = groups[top]
        if not issues:
            continue
        distinct = list(dict.fromkeys(issues))  # dedupe, preserve order
        if len(distinct) == 1:
            entries.append(f"{top}: {distinct[0]}")
        else:
            entries.append(f"{top}: {'; '.join(distinct[:2])}")

    if not entries:
        return "All four tasks fully correct."
    comment = "; ".join(entries) + "."
    if len(comment) > 280:
        comment = comment[:277] + "..."
    return comment


def grade_submission(sub_id: str, sub_root: Path, tmp_root: Path):
    """Returns (marks, comment, full_log_text)."""
    log = [f"===== Grading {sub_id} ====="]
    src_q1 = sub_root / "q1"
    work = tmp_root / sub_id
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    if not src_q1.exists():
        log.append("ERROR: no q1/ directory found in submission.")
        comment = "Submission missing q1/ directory entirely."
        write_log(sub_id, log, tmp_root)
        return 0.0, comment, "\n".join(log)

    # copy only the .py files student submitted (ignore any stray output/input csvs)
    for py in ["q1_t1.py", "q1_t2.py", "q1_t3.py", "q1_t4.py"]:
        src = src_q1 / py
        if src.exists():
            shutil.copy(src, work / py)

    all_results = []
    try:
        a, b, c = grade_t1(work, log)
        all_results.extend([a, b, c])
    except Exception as e:
        log.append(f"[Task1] UNEXPECTED GRADER ERROR: {e}\n{traceback.format_exc()}")
        for name, mx in [("Task1-PartA", T1_PARTA_MARKS), ("Task1-PartB", T1_PARTB_MARKS),
                          ("Task1-PartC", T1_PARTC_MARKS)]:
            t = TaskResult(name, mx)
            t.fail("grader internal error")
            all_results.append(t)

    for grade_fn, name, mx in [(grade_t2, "Task2", T2_MARKS),
                               (grade_t3, "Task3", T3_MARKS),
                               (grade_t4, "Task4", T4_MARKS)]:
        try:
            all_results.append(grade_fn(work, log))
        except Exception as e:
            log.append(f"[{name}] UNEXPECTED GRADER ERROR: {e}\n{traceback.format_exc()}")
            t = TaskResult(name, mx)
            t.fail("grader internal error")
            all_results.append(t)

    total_marks = sum(t.marks for t in all_results)
    comment = build_comment(all_results)

    log.append("")
    log.append("----- Summary -----")
    for t in all_results:
        log.append(f"{t.name}: {t.marks:.2f}/{t.max_marks}")
    log.append(f"TOTAL: {total_marks:.2f}/{TOTAL_MARKS}")
    log.append(f"Comment: {comment}")

    # cleanup temp work dir for this student
    shutil.rmtree(work, ignore_errors=True)

    return round(total_marks, 2), comment, "\n".join(log)


def write_log(sub_id, log_lines, logs_dir):
    (logs_dir / f"{sub_id}.log").write_text("\n".join(log_lines))


def main():
    parser = argparse.ArgumentParser(description="Autograder for CSO606 Q1")
    parser.add_argument("--submissions", default="../recheck", help="path to submissions/ directory")
    parser.add_argument("--out", default="recheck_results.csv", help="output results CSV path")
    parser.add_argument("--logs", default="logs", help="directory for per-student detailed logs")
    args = parser.parse_args()

    submissions_dir = Path(args.submissions)
    logs_dir = Path(args.logs)
    logs_dir.mkdir(parents=True, exist_ok=True)
    tmp_root = Path(".grading_tmp")
    tmp_root.mkdir(exist_ok=True)

    if not submissions_dir.exists():
        print(f"ERROR: submissions directory '{submissions_dir}' does not exist.")
        sys.exit(1)

    rows = []
    sub_ids = sorted([p.name for p in submissions_dir.iterdir() if p.is_dir()])
    if not sub_ids:
        print(f"WARNING: no submission directories found under '{submissions_dir}'.")

    for sub_id in sub_ids:
        sub_root = submissions_dir / sub_id
        print(f"Grading {sub_id} ...", end=" ", flush=True)
        try:
            marks, comment, full_log = grade_submission(sub_id, sub_root, tmp_root)
        except Exception as e:
            marks, comment = 0.0, f"Grader crashed on this submission: {e}"
            full_log = f"UNCAUGHT GRADER EXCEPTION for {sub_id}:\n{traceback.format_exc()}"
        write_log(sub_id, full_log.splitlines(), logs_dir)
        rows.append({"id": sub_id, "marks": marks, "comment": comment})
        print(f"{marks}/{TOTAL_MARKS}")

    results_df = pd.DataFrame(rows, columns=["id", "marks", "comment"])
    results_df.to_csv(args.out, index=False)
    shutil.rmtree(tmp_root, ignore_errors=True)
    print(f"\nDone. Wrote {args.out} ({len(rows)} submissions) and per-student logs to {logs_dir}/")


if __name__ == "__main__":
    main()

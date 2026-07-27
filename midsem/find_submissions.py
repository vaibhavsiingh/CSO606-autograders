"""
Autograder for Q5 (treeEngine.py) with a side-task of collecting Q3(b) perf.txt files.

Improvements over the original script:
  - Per-student try/except so one bad/crashing submission can't kill the whole run.
  - 1-second timeout per testcase (subprocess.run(..., timeout=...)).
  - Handles missing/misnamed scripts, non-executable interpreters, missing expected
    output files, and unreadable output files without crashing.
  - Writes a final CSV (q5_results.csv) with score, total, and which testcases failed.
  - Fixes a latent bug in the original folder-structure detection where handle_sub()
    could be called multiple times per student if there were multiple "Q*" folders.
"""

import csv
import shutil
import subprocess
from pathlib import Path

# ----------------------------- Configuration -----------------------------
SUBMISSIONS_DIR = Path("recheck")
PERF_SUB_DIR = Path("perf_submissions")
TESTCASES_DIR = Path("q6/testcases")
OUTPUTS_DIR = Path("q6/outputs")
RESULTS_CSV = Path("q6_results.csv")
STUD_OUT_FILE = Path("stud_out.txt")
TIME_LIMIT_SEC = 1
PYTHON_BIN = "python3"  # change to "python" if that's what your grading env uses
# ---------------------------------------------------------------------------


def normalise_output(path: Path) -> list[str]:
    """Read a file and return a list of stripped, non-empty lines.
    Returns [] (rather than raising) if the file can't be read."""
    try:
        with open(path, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except (FileNotFoundError, OSError) as e:
        print(f"    [WARN] could not read {path}: {e}")
        return []


def run_python_test(file_path: Path, student_id: str):
    """
    Run every testcase in TESTCASES_DIR against the student's script.

    Returns:
        num_correct (int)
        num_total (int)
        failed_testcases (list[str]) - testcase names, tagged with the reason
                                        when it's not a plain wrong-answer
                                        (e.g. "003(timeout)", "004(exec-error)")
    """
    if not TESTCASES_DIR.exists():
        raise FileNotFoundError(f"testcases directory not found: {TESTCASES_DIR}")
    if not OUTPUTS_DIR.exists():
        raise FileNotFoundError(f"expected-outputs directory not found: {OUTPUTS_DIR}")
    if not file_path.exists():
        raise FileNotFoundError(f"student script not found: {file_path}")

    num_correct = 0
    num_total = 0
    failed_testcases = []

    for testcase in sorted(TESTCASES_DIR.iterdir()):
        if not testcase.is_file():
            continue

        testcase_num = testcase.name.split(".")[0]
        output_file = OUTPUTS_DIR / f"{testcase_num}.out"
        num_total += 1

        if not output_file.exists():
            print(f"    [WARN] missing expected output for testcase {testcase_num}, skipping")
            failed_testcases.append(f"{testcase_num}(no-expected-output)")
            continue

        try:
            with open(testcase, "r") as infile, open(STUD_OUT_FILE, "w") as outfile:
                subprocess.run(
                    [PYTHON_BIN, str(file_path)],
                    stdin=infile,
                    stdout=outfile,
                    stderr=subprocess.DEVNULL,
                    timeout=TIME_LIMIT_SEC,
                    check=False,
                )
        except subprocess.TimeoutExpired:
            failed_testcases.append(f"{testcase_num}(timeout>{TIME_LIMIT_SEC}s)")
            continue
        except (OSError, PermissionError) as e:
            # interpreter missing, script not readable/executable, etc.
            failed_testcases.append(f"{testcase_num}(exec-error:{e.__class__.__name__})")
            continue

        student_output = normalise_output(STUD_OUT_FILE)
        correct_output = normalise_output(output_file)

        if student_output == correct_output:
            num_correct += 1
        else:
            failed_testcases.append(testcase_num)

    print(f"  {student_id} - {file_path.name} : {num_correct}/{num_total}")
    if failed_testcases:
        print(f"    failed testcases: {', '.join(failed_testcases)}")

    return num_correct, num_total, failed_testcases


def handle_sub(sub: Path, student_id: str, results: list):
    """Process one student's submission root `sub`. Appends exactly one
    result row to `results`, regardless of what goes wrong."""
    perf_ques = sub / "Q3" / "b" / "perf.txt"
    tree_ques = sub / "Q5" / "treeEngine.py"

    # --- Q3(b) perf.txt collection ---
    if perf_ques.exists():
        try:
            dest_dir = PERF_SUB_DIR / student_id
            dest_dir.mkdir(exist_ok=True, parents=True)
            shutil.copy(perf_ques, dest_dir / "perf.txt")
        except (OSError, shutil.Error) as e:
            print(f"  [ERROR] {student_id}: failed to copy perf.txt: {e}")

    # --- Q5 treeEngine.py grading ---
    if not tree_ques.exists():
        results.append({
            "student_id": student_id,
            "score": 0,
            "total": 0,
            "failed_testcases": "treeEngine.py not submitted",
        })
        return

    try:
        num_correct, num_total, failed = run_python_test(tree_ques, student_id)
        results.append({
            "student_id": student_id,
            "score": num_correct,
            "total": num_total,
            "failed_testcases": "; ".join(failed) if failed else "none",
        })
    except FileNotFoundError as e:
        print(f"  [ERROR] {student_id}: {e}")
        results.append({
            "student_id": student_id,
            "score": 0,
            "total": 0,
            "failed_testcases": f"grading setup error: {e}",
        })
    except Exception as e:
        # Catch-all: one broken submission should never kill the whole run.
        print(f"  [ERROR] {student_id}: unexpected error: {e}")
        results.append({
            "student_id": student_id,
            "score": 0,
            "total": 0,
            "failed_testcases": f"unexpected error: {e}",
        })


def write_csv(results: list):
    if not results:
        print("No results to write.")
        return
    with open(RESULTS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["student_id", "score", "total", "failed_testcases"])
        writer.writeheader()
        writer.writerows(results)
    print(f"\nResults written to {RESULTS_CSV.resolve()}")


def main():
    if not SUBMISSIONS_DIR.exists():
        print(f"[FATAL] submissions directory not found: {SUBMISSIONS_DIR}")
        return

    PERF_SUB_DIR.mkdir(exist_ok=True)
    results = []

    for stud_sub in sorted(p for p in SUBMISSIONS_DIR.iterdir() if p.is_dir()):
        student_id = stud_sub.name
        print(f"Processing {student_id}...")

        try:
            children = list(stud_sub.iterdir())
        except OSError as e:
            print(f"  [ERROR] could not list {stud_sub}: {e}")
            results.append({
                "student_id": student_id,
                "score": 0,
                "total": 0,
                "failed_testcases": f"could not read submission folder: {e}",
            })
            continue

        # Structure A: submissions/<id>/<id>/Q5/treeEngine.py (nested one level)
        nested = next((c for c in children if c.is_dir() and c.name == student_id), None)
        # Structure B: submissions/<id>/Q5/treeEngine.py (flat)
        is_flat = any(c.is_dir() and c.name.startswith("Q") for c in children)

        try:
            if nested is not None:
                handle_sub(nested, student_id, results)
            elif is_flat:
                handle_sub(stud_sub, student_id, results)
            else:
                print(f"  [WARN] unrecognized submission structure for {student_id}")
                results.append({
                    "student_id": student_id,
                    "score": 0,
                    "total": 0,
                    "failed_testcases": "no recognizable submission structure",
                })
        except Exception as e:
            # Final safety net at the per-student level.
            print(f"  [ERROR] {student_id}: unhandled exception: {e}")
            results.append({
                "student_id": student_id,
                "score": 0,
                "total": 0,
                "failed_testcases": f"unhandled exception: {e}",
            })

    write_csv(results)


if __name__ == "__main__":
    main()
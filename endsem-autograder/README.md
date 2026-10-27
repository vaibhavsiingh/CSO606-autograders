# CSO606 NumPy/Pandas/SciPy Autograder

Grades student submissions by importing their `task1`..`taskN` functions
directly and calling them — it does **not** use `np_runner.py` / `pd_runner.py`
/ `sc_runner.py` from the assignment resources.

## What it checks, per submission file

1. **No explicit `for`/`while` loops** — an AST walk over the whole file
   (`static_checks.py`). Catches loops anywhere, including in helper
   functions the student added, not just inside `task_n` itself.
2. **Correctness** — each task is called against a fixed battery of test
   cases (several small/edge cases + one large "big" case) and compared to
   a reference solution with an appropriate tolerance (`compare.py`,
   `reference_solutions.py`).
3. **Speed** — each call runs in an isolated, timed child process
   (`sandbox.py`). Small cases get 2s, the big case gets 5s
   (`config.TIME_LIMIT_SMALL` / `TIME_LIMIT_BIG`). The big case is the real
   point of this check: it's sized so a genuinely vectorized solution
   finishes in well under a second, while a row-by-row Python loop —
   including one smuggled in via a comprehension instead of `for`/`while`,
   which the AST check can't see — blows past the limit.

A loop violation zeroes that file's marks by default
(`config.LOOP_VIOLATION_MARKS_MULTIPLIER = 0.0`), but correctness/timing
still run and get logged, so you can see whether the logic itself would
otherwise have earned marks.

## Layout expected

```
submissions/
  <student_id>/
    NumPy/np_submission.py
    Pandas/pd_submission.py
    SciPy/sc_submission.py
  <student_id_2>/
    ...
```

Same per-module filenames as the assignment's own `resources/` folder. A
missing file just scores 0 for that module; grading continues.

## Running it

```bash
pip install numpy pandas scipy
python3 grade.py --submissions-dir submissions --output results.csv --logs-dir logs
```

Outputs:
- `results.csv` — one row per student: marks per module, total, whether a
  loop violation was found, a short comment.
- `logs/<student_id>.log` — every test case for every task: pass/fail,
  timing, and the actual mismatch/error detail. This is what you'd check
  by hand for a regrade request.

## Files

| File | Purpose |
|---|---|
| `config.py` | Marks per task, time limits, float tolerances, loop penalty. Edit this first. |
| `test_data.py` | The "input databases" — deterministic (seeded) test cases per task, including the big one. |
| `reference_solutions.py` | Correct implementations used to compute expected outputs. |
| `static_checks.py` | AST-based for/while detector. |
| `sandbox.py` | Runs one `task_n(*args)` call in an isolated, timed subprocess. |
| `compare.py` | Type-aware correctness comparison (arrays, DataFrames, tuples, scalars). |
| `grade.py` | Ties it all together; the script you actually run. |
| `example_submissions/` | Three demo submissions used to sanity-check the grader itself — `good` (should score full marks), `bad_loops` (explicit loops, should score 0), `bad_slow` (loop-free but does row-by-row work via comprehensions — shows the timing check catching what the AST check can't). |

## Assumptions made (nothing in the assignment PDF specifies these — adjust freely in `config.py`)

- **Marks split**: NumPy 2/2/3/3 (10), Pandas 2/3/3 (8), SciPy 3/5 (8) = 26 total,
  roughly Easy=2, Medium=3, Medium-Hard=5.
- **Within a task**, marks are split evenly across its test cases (so failing
  just the big case costs one test case's worth of marks, not the whole task).
- **Tolerance**: `rtol=1e-5, atol=1e-6` for most numeric comparisons;
  `rtol=1e-3, atol=1e-3` specifically for SciPy Task 2 (quadratic curve
  fitting), since that's an iterative least-squares fit rather than a
  closed-form value.
- **Pandas row order/index**: filtered rows are expected to keep their
  original DataFrame index (as the assignment's example output shows); a
  student who calls `.reset_index()` will fail those cases.

## One thing worth knowing if you touch `sandbox.py`

`run_task()` reads the child's result off the `multiprocessing.Queue`
*before* calling `proc.join()`, not after. A `Queue` is backed by a
pipe with a limited OS buffer — for a large result (the big-case array or
DataFrame) the child can block *writing* to that pipe until the parent
reads it. Joining first (waiting for the child to exit before ever
draining the queue) deadlocks in exactly that situation: indistinguishable
from a timeout, except it isn't one, and it would unfairly zero out a
correct big-case answer. Keep `queue.get(timeout=...)` first.

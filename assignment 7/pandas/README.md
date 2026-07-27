# CSO606 Q1 Autograder — "The Lost Research Archive" (40 marks)

## Layout expected
```
submissions/
  <EO_ID_1>/q1/q1_t1.py, q1_t2.py, q1_t3.py, q1_t4.py
  <EO_ID_2>/q1/...
  ...
```

## Quick start
```bash
pip install pandas numpy --break-system-packages   # one-time
python3 grader.py --submissions submissions --out results.csv --logs logs
```
Point `--submissions` at wherever the real `submissions/` folder lives. Outputs:
- `results.csv` — columns `id, marks, comment` (one row per EO ID)
- `logs/<id>.log` — full per-task breakdown, stdout/stderr tails, tracebacks

A run over ~300 submissions takes roughly 5-7 minutes on a single core
(mostly Python subprocess startup time — 4 scripts × 300 students).

## How it works
1. `data/` holds **fixed-seed synthetic** input CSVs (`q1_t*_input.csv`) and
   the corresponding golden/expected outputs (`q1_t*_golden.csv`), generated
   once by `generate_data.py` and checked in — grading is deterministic and
   doesn't regenerate data per run.
2. For each student, each script is copied into an isolated temp directory
   together with the matching input CSV, then run as `python3 q1_tN.py` with
   that directory as `cwd` (so relative filenames like `open("q1_t1_input.csv")`
   resolve correctly), under a 60s timeout.
3. The produced output CSV is compared against golden with **tolerant,
   partial-credit** matching (numeric columns use `rtol=1e-2, atol=1e-2`, not
   exact float equality) rather than all-or-nothing per task.
4. Every failure mode is caught explicitly so one bad submission never kills
   the batch: missing script, missing output file, unparseable CSV, missing
   required column(s), non-zero exit code, uncaught exception, or timeout —
   each gets 0 for that (sub-)task plus a specific note in the log, and
   grading continues to the next task/submission.

## Marks scheme (sums to 40)
| Task | Component | Marks |
|---|---|---|
| 1 | Part A — warmup stats (6 columns × 1 mark each, matched per (pclass,sex) group) | 6 |
| 1 | Part B — `survival_rank` (dense rank per pclass) | 3 |
| 1 | Part C — `mean_rolling_survival` + `max_rolling_survival` (2.5 each) | 5 |
| 2 | `since_reset` (per-row match) | 8 |
| 3 | `smoothened_measurement` (per-row match) | 8 |
| 4 | Hazard-count grid (per-cell match, NaN-aware) | 10 |

Within each (sub-)task, marks scale with the **fraction of groups/rows/cells
that match** — e.g. if 3 of 6 (pclass,sex) groups have a correct `avg_age`,
that column earns half its allotted mark. This gives smoother, fairer partial
credit than all-or-nothing, and the log shows the exact fraction for every
column so you can spot-check or override anything by hand.

## Design decisions worth knowing about (read before trusting blindly)

- **Task 1, Part C order of operations**: rolling window is computed *within
  pclass only* (sorted by fare, `window=5, min_periods=1`), then the
  resulting per-row `rolling_survival` is aggregated by `(pclass, sex)` for
  `mean_rolling_survival` / `max_rolling_survival`. This matches the spec's
  wording exactly but is easy to get subtly wrong (e.g. sorting/grouping by
  `sex` too) — I verified this against the reference solution.

- **Task 2 `since_reset`**: I derived the exact recurrence from your worked
  example (reset rows are forced to `0`; the segment *before the very first
  reset* counts `1, 2, 3, ...` from the start, same as any other segment).
  The synthetic test data deliberately includes a genuine ~12-row prefix
  before any reset (a first attempt at this data accidentally forced a reset
  at row 0, which silently hid this exact bug — worth knowing since it's a
  common off-by-one spot for students).

- **Task 3**: confirmed pandas' `rolling(window=3, min_periods=1).mean()`
  skips NaNs within the window (subject to `min_periods` on non-null count)
  by replaying your worked example by hand — this matches it exactly.
  The grader also sanity-checks that a student's row order matches the
  original input order (via the `experiment` column, if present in their
  output) before comparing, since Task 3 has no natural row key.

- **Task 4 grid comparison is the fuzziest part**, because the spec doesn't
  pin down the exact CSV layout (index column name, column header format,
  row/column order). The grader's loader:
  - detects whether the first column is a y-index (by checking if its values
    match the expected y-set) or falls back to positional row order,
  - coerces column headers to int x-values where possible, falling back to
    positional column order if headers don't match,
  - then reindexes both axes to a canonical order before comparing cell-by-cell.
  - This was tested against a submission that writes fully correct values but
    with **shuffled row and column order** — it still scores full marks — but
    if a student's format is too far from any of these patterns, this task
    gets 0 with `"output grid format unreadable"` and the exception detail in
    the log, which is worth a manual glance rather than assuming a real 0.

- **Timeouts**: 60s per script (`TIMEOUT_SECONDS` at the top of `grader.py`).
  Given the input sizes here (hundreds of rows / ~150 grid cells) this is
  generous; tighten it if you want to penalize inefficient solutions, or
  loosen it if your actual class-provided datasets are much bigger.

- **Tolerance**: `rtol=1e-2, atol=1e-2` (`FLOAT_RTOL`/`FLOAT_ATOL` at the top
  of `grader.py`) — loose enough to not penalize rounding/formatting
  differences, tight enough to catch real logic errors. Adjust if needed.

## Regenerating test data
If you want different/larger synthetic datasets, edit `generate_data.py`
(fixed seed `606`, so reruns are reproducible) and re-run:
```bash
python3 generate_data.py
```
This overwrites everything in `data/`. Note: if you regenerate, any comments
in `grader.py` referencing the current data's exact shape (row/grid counts)
are just illustrative and don't need to change.

## Files
- `reference_solutions.py` — golden logic for all 4 tasks (used only to
  build `data/q1_t*_golden.csv`, not called during grading itself)
- `generate_data.py` — builds the synthetic inputs + goldens
- `grader.py` — the actual autograder (this is what you run)
- `data/` — pre-generated inputs + goldens (checked in, deterministic)
- `submissions/` — put real submissions here (or point `--submissions`
  elsewhere)

## Verified against
Before handing this off, I ran it against six hand-built dummy submissions
covering: a fully correct solution, a solution with realistic bugs (wrong
rolling window, 4- vs 8-neighbor grid, off-by-one reset counting), a
submission where every script crashes with a different exception type, a
submission missing `q1_t2.py` entirely, a submission with a wrong output
column name and a reversed rank, and a submission producing an unparseable
CSV. All scored and logged as expected — see the design notes above for the
specific numbers.

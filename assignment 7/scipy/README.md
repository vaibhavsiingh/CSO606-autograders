# Autograder — Q2: Asteroid Defense System (Aegis Interceptor)

Grades `submissions/<EO_ID>/q2/projectile.py` against 20 generated test
cases (40 marks total, matching the question's mark allocation) and
produces a summary CSV plus a detailed per-student log.

## Files

| File                     | Purpose                                                                 |
|--------------------------|--------------------------------------------------------------------------|
| `reference_solution.py`  | Correct model solution (least-squares fit + `solve_ivp` simulation). Doubles as the answer key generator. |
| `generate_tests.py`      | Builds `tests/` — 20 scenarios spanning the constraint space, with ground truth computed by `reference_solution.py`. Deterministic (fixed RNG seed); re-run any time to regenerate from scratch. |
| `grader.py`              | Main entry point. Runs every submission against every test case, applies partial credit, writes `results.csv` and `logs/<EO_ID>.log`. |
| `tests/`                 | Pre-generated test cases (input + expected output + metadata). Already built — you don't need to re-run `generate_tests.py` unless you want a different/larger suite. |
| `submissions/`           | **Empty — put your real submissions here** (`submissions/<EO_ID>/q2/projectile.py`). |
| `example_submissions/`   | 8 synthetic submissions (correct, crashing, always-guesses-MISS, malformed output, infinite loop, missing file, missing `q2/` dir, and a deliberately imprecise-but-legitimate solver) used to sanity-check the grader end to end. |
| `example_logs/`, `example_results.csv` | Output from grading `example_submissions/` — inspect these to see what "real" output looks like before you run it on actual student code. |

## Setup

```bash
pip install numpy scipy
```

## Usage

```bash
# 1. Put student submissions in submissions/<EO_ID>/q2/projectile.py

# 2. Grade everything
python3 grader.py

# Outputs:
#   results.csv        <- id, marks, comment
#   logs/<EO_ID>.log    <- full per-test breakdown for that student
```

Try it on the bundled examples first:

```bash
python3 grader.py --submissions-dir example_submissions --logs-dir example_logs --output-csv example_results.csv
```

Useful flags (`python3 grader.py --help` for the full list):

- `--timeout-scale 2.0` — multiply every test's timeout (default 15s, 20s for
  the N=100 case) if grading on a slower machine.
- `--submissions-dir / --logs-dir / --output-csv` — relocate I/O.
- `--qdir-name / --script-name` — in case the folder/file naming convention
  changes in a future year.

## How grading works

Each of the 20 test cases has a weight (1–3 marks, sums to 40). The student's
script is run as a subprocess (`python <script> < input.txt`, stdin/stdout,
per the problem's I/O format) with a per-test timeout.

For each test:
- **Crash / timeout / unparseable output → 0** for that test (logged with
  the exit code, a stderr tail, or "timed out").
- **Wrong HIT/MISS decision → 0.**
- **MISS, correctly decided → full marks** (MISS has no time to check).
- **HIT, correct decision:**
  - time within **1e-3s** of the reference → full marks (matches the
    question's stated precision requirement)
  - time within **1.0s** → 60% of the test's marks (right physics, imprecise
    integration — e.g. a coarse fixed-step integrator instead of an adaptive
    one)
  - time off by more than that → 20% of the test's marks (got the
    classification right but the numbers are essentially wrong)

These thresholds are constants at the top of `grader.py`
(`TIME_TOL_FULL`, `TIME_TOL_PARTIAL`, `PARTIAL_CREDIT_FRACTION`,
`MINIMAL_CREDIT_FRACTION`) — tune freely.

Output parsing is lenient about case (`hit`/`HIT`) and trailing blank
lines/whitespace, but not about the actual content — this is logged as a
non-penalizing "note" so you can still see when a submission was cosmetically
off-spec. Tighten `HIT_RE` / `MISS_RE` in `grader.py` if you'd rather enforce
exact-case output.

## Ground truth methodology (why it should be fair)

Both the reference solution and the students fit the *same* noisy
observations with ordinary least squares — a deterministic computation — so
their fitted trajectories should agree to near machine precision regardless
of how much noise was injected. The 1e-3s tolerance is therefore really a
check on the interceptor-side numerical integration, not on how well noise
was handled. `18_stress_high_noise_hit`, `20_close_call_hit`, and
`08_max_n_boundary_hit` are weighted slightly higher (3, 3, 2 marks) as the
scenarios most likely to expose a fragile fit or integrator.

## Test suite coverage (`tests/manifest.json`)

20 cases across: clean/no-noise, light/moderate/heavy noise, N at both
boundaries (5 and 100), drag K at both boundaries (0.001 and 0.1), launch
angle/speed at their boundaries (0–2°, ~90°, speed=1, speed=500), irregular
timestamp spacing, a short observation window requiring large forward
extrapolation, a trajectory that never gets intercepted, first observation
exactly at t=0, and a tight near-blast-radius interception.

Regenerate with `python3 generate_tests.py` (deterministic — same seed
produces the same suite; delete `tests/` first if you want to edit ranges in
the script and rebuild from scratch).

## Assumptions worth double-checking against your actual assignment rules

- Student code is graded via **stdin/stdout**, matching the input format in
  the problem statement. If submissions instead take a file path or CLI
  args, adjust `run_one_test()` in `grader.py`.
- `submissions/<EO_ID>/q2/projectile.py` is the expected path; change via
  `--qdir-name` / `--script-name` if your folder convention differs.
- Marks are reported as a float rounded to 2 decimals; round further in the
  CSV post-hoc if you want whole/half marks only.

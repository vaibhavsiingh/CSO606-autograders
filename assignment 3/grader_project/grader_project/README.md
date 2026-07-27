# Q1 (sed/awk/bash) Grader

## Layout

```
grader_project/
├── grade_all.sh              ← run this to grade everyone
├── weights.conf               ← edit marks, weights, tool rules here
├── reference_solutions/       ← instructor answer key (5 scripts)
├── testcases/
│   ├── build_fixtures.sh      ← generates input/ fixtures for tc1-tc3
│   ├── generate_expected.sh   ← runs reference_solutions/ to lock in expected/
│   └── <script>/tc{1,2,3}/{input,expected}/
├── final_submissions/         ← put real student submissions here (you have this already)
├── mock_final_submissions/    ← three fake students used to test the grader itself
│   ├── perfect_student/   (full marks — sanity check the answer key)
│   ├── bad_student/       (wrong output, forbidden tool, missing script)
│   └── edge_student/      (syntax error, infinite loop, missing output file, wrong tool)
└── grader_output/             ← created when you run grade_all.sh
    ├── grades.csv
    └── per_student/<id>.txt   (full diff/breakdown per student)
```

## Running it

```bash
./grade_all.sh \
    --submissions final_submissions \
    --testcases   testcases \
    --output      grader_output
```

All three flags are optional and default to the paths shown above (relative
to the project root). Each student gets `grader_output/per_student/<id>.txt`
with the full test-by-test breakdown, and one row lands in
`grader_output/grades.csv`.

Try it on the mock students first to see the three failure modes in action:

```bash
./grade_all.sh --submissions mock_final_submissions --output /tmp/demo_output
cat /tmp/demo_output/grades.csv
```

## 1. Adding more test cases

Three test cases (`tc1`, `tc2`, `tc3`) per script currently exist. To add a
`tc4`:

1. **Create the input.** Make a directory `testcases/<script>/tc4/input/`
   and drop in whatever the script expects:
   - `failed_login`, `summary`: a single file `auth.log`
   - `local_filter`: a single file `app.log`
   - `replace`, `remove_debug`: a directory named `source/` containing the
     `.c`/`.h` tree (these two scripts hardcode the directory name
     `source`, per your usage clarification)

   The fastest way is to copy-paste a block from
   `testcases/build_fixtures.sh` into a new `tc4` section, edit the
   content, and re-run that file (it's idempotent — safe to re-run anytime,
   it only touches `input/` directories, never `expected/`).

2. **Generate the expected output** by running the reference solution
   against it:

   ```bash
   ./testcases/generate_expected.sh
   ```

   This regenerates `expected/` for *every* tc, including the new tc4, by
   running `reference_solutions/*.sh` against `testcases/*/tc*/input/`.
   Re-running this is also safe — it doesn't touch input fixtures, only
   expected outputs. Inspect what it produced for `tc4` before trusting it
   (`cat testcases/<script>/tc4/expected/*`) — if the reference solution
   has a bug, this will silently bake that bug into the answer key.

3. **Add a weight** for it in `weights.conf`. Weights are normalized within
   a script and don't strictly need to sum to 1.0 (the grader just does
   `marks = max_marks × Σ(weight_i for each passed tc_i)`), but keeping
   them summed to 1.0 keeps "max_marks" meaningful as the literal max.

   ```
   failed_login_tc4=0.20
   # and rebalance tc1/tc2/tc3 so all four sum to 1.0 if you want max_marks
   # to stay literally accurate
   ```

   If you don't add a weight for a tc, it silently defaults to 0.33 — so
   don't forget this step.

4. Re-run `grade_all.sh`. No code changes needed — it discovers test cases
   by listing whatever's under `testcases/<script>/`, not a hardcoded
   `tc1..tc3` list.

   Actually — one correction: the script loop is hardcoded as
   `TCS=(tc1 tc2 tc3)` near the top of `grade_all.sh`. Add `tc4` to that
   array too:

   ```bash
   TCS=(tc1 tc2 tc3 tc4)
   ```

## 2. Tool restrictions (sed/awk/bash only)

Two independent checks run on every script before it's even executed:

- **Forbidden tools.** `weights.conf`'s `FORBIDDEN_TOOL_PENALTY` (default 1
  mark) is deducted from a script's total for each distinct forbidden
  interpreter found inside it (`python`, `python3`, `perl`, `ruby`,
  `Rscript`, `node`, `php`). This is a deduction, not a hard zero — so a
  script that's 90% sed/awk but calls out to `python3` once still gets
  most of its credit minus the penalty. Detection is static (`grep`), not
  perfect — it won't catch `base64 -d <<< ... | bash` obfuscation, but
  it'll catch normal cases.

- **Required tools.** `weights.conf`'s `REQUIRES_AWK` / `REQUIRES_SED`
  declare which scripts must literally contain the word `awk` / `sed`
  somewhere. If a required tool is absent, the entire script is zeroed
  (not just penalized) — this directly encodes "questions awk-1/2/3 must
  use awk, sed-1/2 must use sed" from the assignment.

  **Important assumption to double check:** the assignment text never
  labels which of the 5 scripts correspond to "awk-1/2/3" vs "sed-1/2".
  I mapped `failed_login`/`summary`/`local_filter` → must-use-awk (since
  `summary.sh` explicitly says "must use awk... to extract... and to
  compute") and `replace`/`remove_debug` → must-use-sed (since they're
  framed as one-shot edits, sed's classic use case). If you intended a
  different split — e.g. you're fine with `replace.sh` using `awk
  gsub(...)` instead of `sed -i` as long as the output is correct — edit
  the two lines in `weights.conf` (or set `ENFORCE_REQUIRED_TOOLS=false`
  to drop this check entirely and grade on output correctness only).

  This matters concretely: `edge_student` in the mock data solves
  `replace.sh` with 100%-correct output using `awk` instead of `sed`, and
  gets zeroed for it under the current mapping. Worth a quick look at
  `mock_final_submissions/edge_student/q1/replace.sh` to decide if that's
  the policy you want.

## 3. Comments, not just marks

Every CSV row's `comments` column has one semicolon-and-pipe-delimited
segment per script, e.g.:

```
failed_login(5.00/5): tc1=PASS; tc2=PASS; tc3=PASS; | summary(0.00/5): tc1=FAIL:mismatch[...]; tc2=FAIL:mismatch[...]; [forbidden tool: python] [required tool 'awk' not used] | ...
```

`FAIL:mismatch[...]` includes the first ~6 lines of `diff expected got`
inline, so you can usually see what went wrong without opening the
per-student file. For the full untruncated diff and a more readable
per-script breakdown, open `grader_output/per_student/<id>.txt`.

## 4. Weights

Edit `weights.conf`:

- `MAX_MARKS_<script>` — total marks for that script (defaults: 5 each, 25
  total, matching the question paper).
- `<script>_tc1` / `_tc2` / `_tc3` — fraction of that script's marks
  awarded if that test case passes. A script's mark is the literal sum:
  `max_marks × (sum of weights of all tc's that passed)`. There's no
  partial credit within a single test case — each test case is exact-match
  pass/fail, per your instruction.

## 5. Output CSV

`grader_output/grades.csv` columns:

```
id, total_marks, max_marks, failed_login, summary, local_filter, replace, remove_debug, comments
```

`id` is the student's folder name under `final_submissions/`, matching
your spec. `total_marks` is the sum across all 5 scripts (capped at 0 from
below per-script, never negative even with forbidden-tool penalties).

## Notes on grading mechanics

- Each script gets a 15-second timeout (`TIMEOUT_SECS` near the top of
  `grade_all.sh`) per test case — an infinite loop costs 15s × 3 = 45s for
  that one script, not an unbounded hang. Bump this if your fixtures are
  large or scripts legitimately need longer.
- `replace.sh` / `remove_debug.sh` are run in a fresh temp sandbox per
  test case with a freshly-copied `source/` tree, since they mutate files
  in place — a student's script can never see another test case's
  leftover state, and the grader's own fixture files are never mutated
  (everything happens on a `cp -r`'d copy).
- A missing script file just zeros that script with a `MISSING SCRIPT`
  comment, rather than crashing the whole run.

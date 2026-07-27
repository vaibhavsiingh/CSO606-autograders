# Q2 Docker Compose Autograder

Grades the "multi-container app with Docker Compose" assignment (20 marks) and
produces per-student JSON reports plus a summary CSV.

## Setup

```bash
pip install pyyaml --break-system-packages   # only external dependency
```

You also need **Docker + the `docker compose` v2 plugin** installed and running
on the machine you grade on — the script actually builds and runs each
submission's containers to verify real behaviour, not just static files.

## Expected layout (run the script from the folder containing these two)

```
.
├── grader.py
├── final_submissions/
│   ├── 21f1000123_JohnDoe/
│   │   └── q2/
│   │       ├── docker-compose.yml
│   │       ├── api/{Dockerfile, server.py}
│   │       └── tester/{Dockerfile, test_api.py}
│   ├── 21f2000456/
│   │   └── q2/...
│   └── ...
└── roll_list.csv        # must have a column named "EO ID"
```

## Running it

```bash
python3 grader.py \
  --submissions final_submissions \
  --roll-list roll_list.csv \
  --output grading_output
```

Add `--static-only` to skip the actual `docker compose build/up` step (e.g. to
sanity-check matching/file-structure quickly, or if Docker isn't available on
the current machine — in that case api/tester marks will be 0 for everyone,
since those can only be verified by actually running the containers).

## Outputs (in `grading_output/`)

- **`student_reports/<roll>.json`** — one file per student with:
  - `marks` — breakdown across api / tester / dockerfiles / compose + total
  - `issues` — every problem found, each with a verbose `detail` (for you/TAs)
    and a short `brief` (student-facing)
  - `student_comment` — the short, issues-only summary (or `"All checks
    passed."` if nothing was wrong)
  - `grader_comment` — the detailed, issues-only summary for the instructor
  - `dynamic_run` — raw `api`/`tester` container logs and build/run status,
    for manually double-checking anything that looks off
  - `match_type` / `match_note` — how the roll number was matched to a folder
    (`exact`, `substring`, `ambiguous`, or `missing`)
- **`grades.csv`** — your original `roll_list.csv` with two new columns,
  `Marks` and `Comments` (the short student-facing comment)
- **`unmatched_directories.txt`** — submission folders that didn't match any
  roll number (e.g. typos too different for the substring match, or extra
  junk in the folder) — worth a manual look

## How matching works

For each roll number in `roll_list.csv`:
1. Exact folder-name match, if one exists.
2. Otherwise, a folder whose name **contains** the roll number as a substring
   — but only if exactly one such folder exists. If more than one folder
   contains the roll number, it's flagged `ambiguous` (0 marks, logged) rather
   than guessed at, since picking wrong would misattribute a grade.

## Rubric breakdown implemented

| Section | Marks | How it's checked |
|---|---|---|
| API Service | 6 | 1.5 marks per endpoint (`/health`, `/square/7`, `/reverse/...`, `/sum?...`), verified via the tester's actual output after a real `docker compose up` |
| Tester Service | 6 | 4 marks for the exact 5-line stdout match in order, 1 mark for exit code 0 only on genuine success, 1 mark for addressing the API via `http://api:5000` rather than localhost |
| Dockerfiles | 2 | 1 mark each for api/tester: python base image + `WORKDIR` + correct script referenced in CMD/ENTRYPOINT |
| Compose | 6 | 1 mark both services defined, 1 mark correct build contexts, 2 marks api healthcheck present & sane, 1 mark tester `depends_on: condition: service_healthy`, 1 mark no `network_mode: host` |

All weightings are constants near the top of `grader.py`
(`MAX_MARKS`, and the per-check point values inside each `grade_*` function)
if you want to rebalance them.

## Notes / caveats

- Timeouts (build/up/tester-wait/down) are tunable constants near the top of
  the file if your machine or students' images are slow.
- Comments are deliberately **issues-only** — a fully correct submission gets
  `"All checks passed."` with no filler praise.
- The grader always cleans up after itself (`docker compose down -v
  --remove-orphans`) before and after each submission, so one student's stale
  containers/networks can't bleed into the next student's run.

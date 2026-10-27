# CSO606 Autograders

Autograders and grading helpers for **CSO 606: Toolkit for Programmers**.

## Contents

| Folder | What it grades |
|---|---|
| `assignment 1/` | Remarks and final-marks generation |
| `assignment 2/` | Download / organise / evaluate scripting tasks |
| `assignment 3/` | sed / awk / bash tasks |
| `assignment 5/` | Multi-container app with Docker Compose |
| `assignment 7/` | Pandas and SciPy tasks |
| `midsem/` | Midsem Q6 test cases and submission checks |
| `endsem-autograder/` | Endsem NumPy / Pandas / SciPy tasks (loop check, correctness, timing) |
| `new questions/` | Drafts of new questions and reference solutions |

Top-level scripts (`unzip-all.py`, `structure.py`, `remove_level.py`,
`final_csv_creator.py`) unzip, restructure and collate submissions before or
after grading.

Most graders expect submissions under `submissions/<student_id>/`. See the
README in each folder for details.

## Note

Student submissions, rosters and marks (`*.csv`, `*.xlsx`) are kept out of
this repo via `.gitignore`. Don't commit them.

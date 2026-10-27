"""
Central configuration for the CSO606 NumPy/Pandas/SciPy autograder.

Nothing about test *data* or *correctness logic* lives here — this file
only holds numbers you're likely to want to tune per-run (marks, time
limits, tolerances). Edit these, not the grading logic.
"""

# ---------------------------------------------------------------------------
# Marks per task. Assignment PDF doesn't specify a marks split, so this is
# an assumption — Easy=2, Medium=3, Medium-Hard=4. Adjust freely; grade.py
# reads everything from here, nothing is hardcoded downstream.
# ---------------------------------------------------------------------------
MARKS = {
    "NumPy": {"task1": 2, "task2": 2, "task3": 3, "task4": 3},      # 10
    "Pandas": {"task1": 2, "task2": 3, "task3": 3},                  # 8  (task3 is heavier)
    "SciPy": {"task1": 3, "task2": 5},                               # 8  (curve fitting is harder)
}

# ---------------------------------------------------------------------------
# Per-task-call time limits (seconds), keyed by test case size.
# "small" cases must be fast regardless of implementation.
# "big" cases are the real vectorization filter: a hidden Python-level loop
# over the big arrays/frame will blow through this even though it might
# sneak past the AST loop-checker (e.g. via a comprehension).
# ---------------------------------------------------------------------------
TIME_LIMIT_SMALL = 2.0
TIME_LIMIT_BIG = 5.0

# ---------------------------------------------------------------------------
# Numerical comparison tolerance for float outputs (np.allclose-style).
# ---------------------------------------------------------------------------
RTOL = 1e-5
ATOL = 1e-6

# Curve fitting (SciPy task2) is solved numerically (least squares) and is
# a harder target to hit exactly than the closed-form integral, so it gets
# a looser tolerance.
CURVE_FIT_RTOL = 1e-3
CURVE_FIT_ATOL = 1e-3

# ---------------------------------------------------------------------------
# What happens to a file's marks if the AST checker finds an explicit
# for/while loop anywhere in it (including in helper functions the student
# defined). 0.0 = zero marks for that whole module file, no partial credit.
# Set to e.g. 0.5 if you'd rather halve the marks than zero them.
# ---------------------------------------------------------------------------
LOOP_VIOLATION_MARKS_MULTIPLIER = 0.0

# Submission file naming, matches the assignment's resources/ layout.
SUBMISSION_FILENAMES = {
    "NumPy": "np_submission.py",
    "Pandas": "pd_submission.py",
    "SciPy": "sc_submission.py",
}

"""
Builds the input databases every submission is graded against.

Each task maps to a list of test cases. A test case is a dict:
    {
        "name":    short label used in logs,
        "args":    tuple of positional args passed to task_n(*args),
        "timeout": per-call time limit in seconds (config.TIME_LIMIT_*),
    }

Cases are generated once with a fixed RNG seed so every grading run (and
every student) sees identical data — reproducible and comparable.

The "big" case per module is deliberately large enough that a row/element
-wise Python loop takes seconds, while a properly vectorized NumPy/Pandas
solution finishes in well under TIME_LIMIT_BIG.
"""

import numpy as np
import pandas as pd

from config import TIME_LIMIT_SMALL, TIME_LIMIT_BIG

_rng = np.random.default_rng(606)


# ---------------------------------------------------------------------------
# NumPy — sensors (rows) x time instants (columns)
# ---------------------------------------------------------------------------
def _numpy_matrix(n_sensors, n_readings, low=0, high=100, decimals=2):
    return np.round(_rng.uniform(low, high, size=(n_sensors, n_readings)), decimals)


def build_numpy_cases():
    example = np.array([
        [12, 15, 18, 20, 19],
        [10, 14, 16, 18, 17],
        [13, 16, 20, 21, 22],
        [11, 13, 15, 17, 18],
        [14, 17, 21, 23, 24],
    ], dtype=float)

    small_random = _numpy_matrix(6, 4)
    negative_values = _numpy_matrix(5, 5, low=-50, high=50)
    single_reading = _numpy_matrix(4, 1)          # edge case: 1 column, avg == the value itself
    tie_break = np.array([                          # edge case: two sensors share the max average
        [10.0, 10.0, 10.0],
        [5.0, 5.0, 5.0],
        [10.0, 10.0, 10.0],
    ])
    big = _numpy_matrix(500, 3000)                 # 1.5M cells

    cases = [
        {"name": "pdf_example", "args": (example,), "timeout": TIME_LIMIT_SMALL},
        {"name": "small_random_6x4", "args": (small_random,), "timeout": TIME_LIMIT_SMALL},
        {"name": "negative_values_5x5", "args": (negative_values,), "timeout": TIME_LIMIT_SMALL},
        {"name": "single_reading_4x1", "args": (single_reading,), "timeout": TIME_LIMIT_SMALL},
        {"name": "tie_break_3x3", "args": (tie_break,), "timeout": TIME_LIMIT_SMALL},
        {"name": "big_500x3000", "args": (big,), "timeout": TIME_LIMIT_BIG},
    ]
    return {"task1": cases, "task2": cases, "task3": cases, "task4": cases}


# ---------------------------------------------------------------------------
# Pandas — student roster
# ---------------------------------------------------------------------------
def _pdf_example_df():
    return pd.DataFrame({
        "Name": ["Alice", "Bob", "Charlie", "David", "Eva", "Frank", "Grace", "Helen"],
        "Department": ["CS", "EE", "CS", "ME", "EE", "CS", "ME", "CS"],
        "Age": [20, 21, 22, 20, 23, 21, 22, 20],
        "Score": [78, np.nan, 91, 63, 55, 39, 84, np.nan],
    })


def _random_roster(n, depts, seed_offset, nan_frac=0.15):
    names = [f"S{seed_offset}_{i}" for i in range(n)]
    department = _rng.choice(depts, size=n)
    age = _rng.integers(18, 26, size=n)
    score = _rng.uniform(30, 100, size=n).round(1)
    nan_mask = _rng.random(n) < nan_frac
    score[nan_mask] = np.nan
    return pd.DataFrame({"Name": names, "Department": department, "Age": age, "Score": score})


def build_pandas_cases():
    example = _pdf_example_df()
    small_random = _random_roster(20, ["CS", "EE", "ME"], seed_offset=1)
    no_missing = _random_roster(10, ["CS", "EE"], seed_offset=2, nan_frac=0.0)   # edge: no NaNs at all
    all_missing = pd.DataFrame({                                                  # edge: every score NaN
        "Name": ["X1", "X2", "X3"],
        "Department": ["CS", "CS", "EE"],
        "Age": [20, 21, 22],
        "Score": [np.nan, np.nan, np.nan],
    })
    single_dept = _random_roster(8, ["ME"], seed_offset=3)                        # edge: one department only
    big = _random_roster(200_000, ["CS", "EE", "ME", "CE", "AE"], seed_offset=4)

    common = [
        {"name": "pdf_example", "args": (example,), "timeout": TIME_LIMIT_SMALL},
        {"name": "small_random_20", "args": (small_random,), "timeout": TIME_LIMIT_SMALL},
        {"name": "no_missing_scores", "args": (no_missing,), "timeout": TIME_LIMIT_SMALL},
        {"name": "all_missing_scores", "args": (all_missing,), "timeout": TIME_LIMIT_SMALL},
        {"name": "single_department", "args": (single_dept,), "timeout": TIME_LIMIT_SMALL},
        {"name": "big_200000_rows", "args": (big,), "timeout": TIME_LIMIT_BIG},
    ]
    return {"task1": common, "task2": common, "task3": common}


# ---------------------------------------------------------------------------
# SciPy
# ---------------------------------------------------------------------------
def build_scipy_cases():
    task1_cases = [
        {"name": "pdf_example", "args": ([2, 3, 1], 0, 2), "timeout": TIME_LIMIT_SMALL},
        {"name": "negative_bounds", "args": ([1, -2, 4], -3, 3), "timeout": TIME_LIMIT_SMALL},
        {"name": "no_quadratic_term", "args": ([0, 5, -1], 0, 10), "timeout": TIME_LIMIT_SMALL},
        {"name": "all_zero_coeffs", "args": ([0, 0, 0], -5, 5), "timeout": TIME_LIMIT_SMALL},
        {"name": "reversed_bounds", "args": ([1, 1, 1], 5, -5), "timeout": TIME_LIMIT_SMALL},
        {"name": "wide_bounds", "args": ([0.5, -3.2, 7.1], -1000, 1000), "timeout": TIME_LIMIT_BIG},
    ]

    def _xy(n, a, b, c, noise, seed_offset):
        x = np.linspace(-10, 10, n)
        y = a * x**2 + b * x + c + _rng.normal(0, noise, size=n)
        return x, y

    x1, y1 = np.array([0, 1, 2, 3]), np.array([1, 6, 17, 34])  # pdf example (exact quadratic)
    x2, y2 = _xy(30, 3, -2, 5, noise=0.5, seed_offset=1)
    x3, y3 = _xy(15, -1, 0, 2, noise=0.2, seed_offset=2)        # negative leading coeff
    x4, y4 = _xy(50, 0, 4, -3, noise=0.3, seed_offset=3)         # linear (a≈0)
    x_big, y_big = _xy(100_000, 1.7, -0.5, 2.2, noise=1.0, seed_offset=4)

    task2_cases = [
        {"name": "pdf_example", "args": (x1, y1), "timeout": TIME_LIMIT_SMALL},
        {"name": "noisy_30pts", "args": (x2, y2), "timeout": TIME_LIMIT_SMALL},
        {"name": "negative_leading_coeff", "args": (x3, y3), "timeout": TIME_LIMIT_SMALL},
        {"name": "near_linear", "args": (x4, y4), "timeout": TIME_LIMIT_SMALL},
        {"name": "big_100000_points", "args": (x_big, y_big), "timeout": TIME_LIMIT_BIG},
    ]

    return {"task1": task1_cases, "task2": task2_cases}


def build_all_cases():
    return {
        "NumPy": build_numpy_cases(),
        "Pandas": build_pandas_cases(),
        "SciPy": build_scipy_cases(),
    }

"""
Comparing outputs isn't one-size-fits-all: NumPy tasks return arrays or a
plain int, Pandas tasks return DataFrames, SciPy tasks return a float or a
3-tuple of fit coefficients. Each comparator returns (passed: bool, detail: str).
"""

import numpy as np
import pandas as pd

from config import RTOL, ATOL, CURVE_FIT_RTOL, CURVE_FIT_ATOL


def _fail(msg):
    return False, msg


# ---------------------------------------------------------------------------
# NumPy
# ---------------------------------------------------------------------------
def cmp_np_task1(actual, expected):
    try:
        actual = np.asarray(actual, dtype=float)
    except Exception as e:
        return _fail(f"could not interpret result as an array: {e}")
    if actual.shape != expected.shape:
        return _fail(f"shape mismatch: got {actual.shape}, expected {expected.shape}")
    if not np.allclose(actual, expected, rtol=RTOL, atol=ATOL):
        return _fail(f"values differ: got {actual}, expected {expected}")
    return True, "ok"


def cmp_np_task2(actual, expected):
    try:
        actual_int = int(actual)
    except Exception as e:
        return _fail(f"result is not int-convertible: {e!r} ({e})")
    if actual_int != int(expected):
        return _fail(f"got sensor {actual_int}, expected {int(expected)}")
    return True, "ok"


def cmp_np_task3(actual, expected):
    return cmp_np_task1(actual, expected)  # same shape/tolerance logic


def cmp_np_task4(actual, expected):
    try:
        actual = np.asarray(actual)
    except Exception as e:
        return _fail(f"could not interpret result as an array: {e}")
    if actual.shape != expected.shape:
        return _fail(f"shape mismatch: got {actual.shape}, expected {expected.shape}")
    if not np.array_equal(actual.astype(int), expected.astype(int)):
        return _fail(f"values differ: got {actual}, expected {expected}")
    return True, "ok"


# ---------------------------------------------------------------------------
# Pandas
# ---------------------------------------------------------------------------
def _cmp_dataframe(actual, expected, sort_cols=False):
    if not isinstance(actual, (pd.DataFrame, pd.Series)):
        return _fail(f"result is not a DataFrame/Series (got {type(actual).__name__})")
    if isinstance(actual, pd.Series):
        actual = actual.to_frame()

    try:
        pd.testing.assert_frame_equal(
            actual.sort_index(axis=0).sort_index(axis=1) if sort_cols else actual.sort_index(axis=0),
            expected.sort_index(axis=0).sort_index(axis=1) if sort_cols else expected.sort_index(axis=0),
            check_dtype=False,
            check_exact=False,
            rtol=RTOL,
            atol=ATOL,
        )
        return True, "ok"
    except AssertionError as e:
        return _fail(f"DataFrame mismatch:\n{e}")


def cmp_pd_task1(actual, expected):
    return _cmp_dataframe(actual, expected)


def cmp_pd_task2(actual, expected):
    return _cmp_dataframe(actual, expected)


def cmp_pd_task3(actual, expected):
    return _cmp_dataframe(actual, expected, sort_cols=True)


# ---------------------------------------------------------------------------
# SciPy
# ---------------------------------------------------------------------------
def cmp_sc_task1(actual, expected):
    try:
        actual_f = float(actual)
    except Exception as e:
        return _fail(f"result is not float-convertible: {e!r} ({e})")
    if not np.isclose(actual_f, expected, rtol=RTOL, atol=ATOL):
        return _fail(f"got {actual_f}, expected {expected}")
    return True, "ok"


def cmp_sc_task2(actual, expected):
    try:
        actual_tuple = tuple(float(v) for v in actual)
    except Exception as e:
        return _fail(f"result is not a 3-tuple of floats: {e!r} ({e})")
    if len(actual_tuple) != 3:
        return _fail(f"expected a 3-tuple (a, b, c), got length {len(actual_tuple)}")
    if not np.allclose(actual_tuple, expected, rtol=CURVE_FIT_RTOL, atol=CURVE_FIT_ATOL):
        return _fail(f"got {actual_tuple}, expected {tuple(expected)}")
    return True, "ok"


COMPARATORS = {
    "NumPy": {"task1": cmp_np_task1, "task2": cmp_np_task2, "task3": cmp_np_task3, "task4": cmp_np_task4},
    "Pandas": {"task1": cmp_pd_task1, "task2": cmp_pd_task2, "task3": cmp_pd_task3},
    "SciPy": {"task1": cmp_sc_task1, "task2": cmp_sc_task2},
}

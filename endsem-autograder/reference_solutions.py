"""
Reference (correct, vectorized) solutions for every task. grade.py calls
these directly — not through a subprocess, not through the runner — to
compute the expected output for each test case, then compares it against
whatever the student's task_n() returned.
"""

import numpy as np
import pandas as pd
from scipy import optimize


# ---------------------------------------------------------------------------
# NumPy
# ---------------------------------------------------------------------------
def np_task1(data):
    return data.mean(axis=1)


def np_task2(data):
    return int(np.argmax(data.mean(axis=1))) + 1


def np_task3(data):
    return data - data.mean(axis=1, keepdims=True)


def np_task4(data):
    avg = data.mean(axis=1, keepdims=True)
    return (data > avg).sum(axis=0)


# ---------------------------------------------------------------------------
# Pandas
# ---------------------------------------------------------------------------
def pd_task1(data):
    return data[data["Score"].isna()]


def pd_task2(data):
    return data[(data["Department"] == "CS") & (data["Score"] > 70) & (data["Age"] <= 21)]


def pd_task3(data):
    return data.groupby("Department").agg(Score=("Score", "mean"), Age=("Age", "max"))


# ---------------------------------------------------------------------------
# SciPy
# ---------------------------------------------------------------------------
def sc_task1(coefficients, lower, upper):
    a, b, c = coefficients
    # closed form antiderivative, avoids needing scipy.integrate.quad as an
    # instructor dependency (a plain analytic check is faster and exact)
    F = lambda x: a * x**3 / 3 + b * x**2 / 2 + c * x
    return F(upper) - F(lower)


def sc_task2(x, y):
    a, b, c = np.polyfit(x, y, 2)
    return (a, b, c)


NUMPY_REFS = {"task1": np_task1, "task2": np_task2, "task3": np_task3, "task4": np_task4}
PANDAS_REFS = {"task1": pd_task1, "task2": pd_task2, "task3": pd_task3}
SCIPY_REFS = {"task1": sc_task1, "task2": sc_task2}

ALL_REFS = {"NumPy": NUMPY_REFS, "Pandas": PANDAS_REFS, "SciPy": SCIPY_REFS}

"""
solution_key.py  (INSTRUCTOR USE ONLY -- do not distribute to students)
-------------------------------------------------------------------------
Reference implementation that produces the exact expected output for every
task in the assignment. Run this after generate_data.py. Grading is then a
direct comparison (pandas.testing.assert_frame_equal / read_csv + compare)
between a student's submitted file and the matching file in
instructor_solutions/.

Usage:
    python generate_data.py
    python solution_key.py
"""

import os
import numpy as np
import pandas as pd

IN_DIR = "datasets"
OUT_DIR = "instructor_solutions"
os.makedirs(OUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Warmup
# ---------------------------------------------------------------------------
def solve_warmup():
    df = pd.read_csv(os.path.join(IN_DIR, "titanic.csv"))

    # Q1: survival % by class and sex
    q1 = (
        (df.groupby(["pclass", "sex"])["survived"].mean() * 100)
        .round(2)
        .rename("survival_pct")
        .reset_index()
        .sort_values(["pclass", "sex"])
        .reset_index(drop=True)
    )
    q1.to_csv(os.path.join(OUT_DIR, "warmup_q1.csv"), index=False)

    # Q2: oldest survivor per class (ignore missing age; tie -> lowest
    # original row index)
    surv = df[df["survived"] == 1].dropna(subset=["age"]).copy()
    surv["passenger_index"] = surv.index
    q2 = (
        surv.sort_values(["pclass", "age", "passenger_index"],
                          ascending=[True, False, True])
        .groupby("pclass")
        .first()[["passenger_index", "age", "sex"]]
        .reset_index()
    )
    q2.to_csv(os.path.join(OUT_DIR, "warmup_q2.csv"), index=False)

    # Q3: survival % by family-size bucket
    df2 = df.copy()
    df2["family_size"] = df2["sibsp"] + df2["parch"] + 1
    df2["family_bucket"] = pd.cut(
        df2["family_size"], bins=[0, 1, 4, np.inf],
        labels=["alone", "small", "large"]
    )
    q3 = (
        (df2.groupby("family_bucket")["survived"].mean() * 100)
        .round(2)
        .reindex(["alone", "small", "large"])
        .rename("survival_pct")
        .reset_index()
    )
    q3.to_csv(os.path.join(OUT_DIR, "warmup_q3.csv"), index=False)
    print("[warmup] wrote warmup_q1.csv, warmup_q2.csv, warmup_q3.csv")


# ---------------------------------------------------------------------------
# Puzzle 1: distance back to the previous zero
# ---------------------------------------------------------------------------
def solve_puzzle1():
    df = pd.read_csv(os.path.join(IN_DIR, "puzzle1_input.csv"))
    x = df["X"].values
    idx = np.arange(len(x))
    zero_idx = np.where(x == 0, idx, -1)
    last_zero = pd.Series(zero_idx).cummax().values
    y = idx - last_zero
    y = np.where(x == 0, 0, y)
    df["Y"] = y
    df.to_csv(os.path.join(OUT_DIR, "puzzle1_output.csv"), index=False)
    print("[puzzle1] wrote puzzle1_output.csv")


# ---------------------------------------------------------------------------
# Puzzle 2: grouped rolling mean (window=3) ignoring NaN
# ---------------------------------------------------------------------------
def solve_puzzle2():
    df = pd.read_csv(os.path.join(IN_DIR, "puzzle2_input.csv"))
    result = (
        df.groupby("group")["value"]
        .rolling(window=3, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
        .sort_index()
    )
    out = df.copy()
    out["rolling_mean"] = result
    out.to_csv(os.path.join(OUT_DIR, "puzzle2_output.csv"), index=False)
    print("[puzzle2] wrote puzzle2_output.csv")


# ---------------------------------------------------------------------------
# Interesting problem: Minesweeper final grid
# ---------------------------------------------------------------------------
def solve_minesweeper():
    df = pd.read_csv(os.path.join(IN_DIR, "minesweeper_input.csv"))
    grid_x = df["x"].max() + 1
    grid_y = df["y"].max() + 1

    mine_lookup = {(r.x, r.y): r.mine for r in df.itertuples()}

    def adjacent_count(x, y):
        total = 0
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                total += mine_lookup.get((x + dx, y + dy), 0)
        return total

    df["adjacent"] = [adjacent_count(r.x, r.y) for r in df.itertuples()]
    df.loc[df["mine"] == 1, "adjacent"] = np.nan

    grid = df.pivot(index="y", columns="x", values="adjacent")
    grid.index.name = "y"
    grid.columns.name = "x"
    grid.to_csv(os.path.join(OUT_DIR, "minesweeper_output.csv"))
    print(f"[minesweeper] wrote minesweeper_output.csv, grid shape {grid.shape}")


if __name__ == "__main__":
    solve_warmup()
    solve_puzzle1()
    solve_puzzle2()
    solve_minesweeper()
    print("\nAll reference outputs written to ./instructor_solutions/")
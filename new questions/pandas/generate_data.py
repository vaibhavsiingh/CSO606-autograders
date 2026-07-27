"""
generate_data.py
-----------------
Generates every input file needed for the Pandas/SciPy assignment.
Run this once and distribute the resulting files in `datasets/` to students
alongside the assignment. All randomness is seeded, so re-running this
script always produces byte-identical files -- this is what removes any
"discrepancy" risk during grading.

Usage:
    python generate_data.py
"""

import os
import numpy as np
import pandas as pd

OUT_DIR = "datasets"
os.makedirs(OUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Warmup dataset: Titanic (a standard, widely used public dataset)
# ---------------------------------------------------------------------------
def make_warmup_dataset():
    url = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/titanic.csv"
    df = pd.read_csv(url)
    # Freeze a local copy so every student works off the exact same file,
    # independent of any future changes to the upstream source.
    df.to_csv(os.path.join(OUT_DIR, "titanic.csv"), index=False)
    print(f"[warmup] wrote titanic.csv with shape {df.shape}")


# ---------------------------------------------------------------------------
# Puzzle 1 input: integer column with scattered zeros
# ---------------------------------------------------------------------------
def make_puzzle1_dataset(n_rows=60, seed=101):
    rng = np.random.default_rng(seed)
    x = rng.integers(0, 10, size=n_rows)  # values 0-9, zeros included
    df = pd.DataFrame({"X": x})
    df.to_csv(os.path.join(OUT_DIR, "puzzle1_input.csv"), index=False)
    print(f"[puzzle1] wrote puzzle1_input.csv with {n_rows} rows, "
          f"{int((x == 0).sum())} zeros")


# ---------------------------------------------------------------------------
# Puzzle 2 input: grouped numeric series with scattered NaNs
# ---------------------------------------------------------------------------
def make_puzzle2_dataset(n_rows=80, n_groups=5, nan_frac=0.15, seed=202):
    rng = np.random.default_rng(seed)
    groups = rng.choice(list("abcde")[:n_groups], size=n_rows)
    values = rng.uniform(1, 20, size=n_rows).round(2)
    nan_mask = rng.random(n_rows) < nan_frac
    values[nan_mask] = np.nan
    df = pd.DataFrame({"group": groups, "value": values})
    df.to_csv(os.path.join(OUT_DIR, "puzzle2_input.csv"), index=False)
    print(f"[puzzle2] wrote puzzle2_input.csv with {n_rows} rows, "
          f"{int(nan_mask.sum())} NaNs across {n_groups} groups")


# ---------------------------------------------------------------------------
# Minesweeper input: pre-generated mine layout for a fixed grid size
# ---------------------------------------------------------------------------
def make_minesweeper_dataset(grid_x=10, grid_y=8, p_mine=0.4, seed=303):
    rng = np.random.default_rng(seed)
    coords = pd.DataFrame(
        [(x, y) for x in range(grid_x) for y in range(grid_y)],
        columns=["x", "y"],
    )
    coords["mine"] = (rng.random(len(coords)) < p_mine).astype(int)
    coords.to_csv(os.path.join(OUT_DIR, "minesweeper_input.csv"), index=False)
    print(f"[minesweeper] wrote minesweeper_input.csv, grid {grid_x}x{grid_y}, "
          f"{int(coords['mine'].sum())} mines")


if __name__ == "__main__":
    make_warmup_dataset()
    make_puzzle1_dataset()
    make_puzzle2_dataset()
    make_minesweeper_dataset()
    print("\nAll datasets written to ./datasets/")
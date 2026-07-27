import numpy as np
import pandas as pd


def solve_t1(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # ---- Part A: warmup stats per (pclass, sex) ----
    grp = df.groupby(['pclass', 'sex'])
    partA = grp.agg(
        passenger_count=('survived', 'size'),
        survivor_count=('survived', 'sum'),
        avg_age=('age', 'mean'),
        median_fare=('fare', 'median'),
        age_std=('age', 'std'),
    ).reset_index()
    partA['survival_pct'] = 100 * grp['survived'].mean().reset_index(drop=True)

    # ---- Part C: rolling survival trend ----
    df_sorted = df.sort_values(['pclass', 'fare'], kind='mergesort')
    df_sorted['rolling_survival'] = (
        df_sorted.groupby('pclass')['survived']
        .transform(lambda s: s.rolling(window=5, min_periods=1).mean())
    )
    rolling_stats = (
        df_sorted.groupby(['pclass', 'sex'])['rolling_survival']
        .agg(mean_rolling_survival='mean', max_rolling_survival='max')
        .reset_index()
    )

    out = partA.merge(rolling_stats, on=['pclass', 'sex'], how='left')

    # ---- Part B: dense rank of survival_pct within pclass (descending) ----
    out['survival_rank'] = (
        out.groupby('pclass')['survival_pct']
        .rank(method='dense', ascending=False)
        .astype(int)
    )

    cols = [
        'pclass', 'sex', 'passenger_count', 'survivor_count', 'survival_pct',
        'avg_age', 'median_fare', 'age_std', 'survival_rank',
        'mean_rolling_survival', 'max_rolling_survival'
    ]
    out = out[cols].sort_values(['pclass', 'sex']).reset_index(drop=True)
    return out


def solve_t2(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    reset_flag = (df['signal'] == 0)
    group = reset_flag.cumsum().shift(1, fill_value=0)
    since_reset = df.groupby(group).cumcount() + 1
    since_reset[reset_flag.values] = 0
    df['since_reset'] = since_reset.values
    return df


def solve_t3(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['smoothened_measurement'] = (
        df.groupby('experiment')['measurement']
        .transform(lambda s: s.rolling(window=3, min_periods=1).mean())
    )
    return df


def solve_t4(df: pd.DataFrame) -> pd.DataFrame:
    xs = sorted(df['x'].unique())
    ys = sorted(df['y'].unique())
    x_index = {x: i for i, x in enumerate(xs)}
    y_index = {y: i for i, y in enumerate(ys)}

    hazard_grid = np.zeros((len(ys), len(xs)), dtype=int)
    for _, row in df.iterrows():
        hazard_grid[y_index[row['y']], x_index[row['x']]] = int(row['hazard'])

    result = np.zeros((len(ys), len(xs)), dtype=float)
    H, W = len(ys), len(xs)
    for yi in range(H):
        for xi in range(W):
            if hazard_grid[yi, xi] == 1:
                result[yi, xi] = np.nan
                continue
            total = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny, nx = yi + dy, xi + dx
                    if 0 <= ny < H and 0 <= nx < W:
                        total += hazard_grid[ny, nx]
            result[yi, xi] = total

    out = pd.DataFrame(result, index=ys, columns=xs)
    out.index.name = 'y'
    return out

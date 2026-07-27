import pandas as pd

def solve_t1(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # ---- normalize column names to match original schema ----
    rename_map = {
        'Survived': 'survived',
        'Pclass': 'pclass',
        'Sex': 'sex',
        'Age': 'age',
        'Fare': 'fare',
    }
    df = df.rename(columns=rename_map)

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

df = pd.read_csv("data/titanic.csv")
out = solve_t1(df)
out.to_csv('data/titanic_golden.csv')
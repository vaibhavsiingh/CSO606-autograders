"""
Generates deterministic synthetic input CSVs + golden output CSVs for
CSO606 Q1 Tasks 1-4. Run once (fixed seed => reproducible). Outputs go to ./data/
"""
import numpy as np
import pandas as pd
from pathlib import Path
import reference_solutions as ref

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

RNG = np.random.default_rng(606)


def gen_t1(n=420):
    pclass = RNG.choice([1, 2, 3], size=n, p=[0.25, 0.3, 0.45])
    sex = RNG.choice(['male', 'female'], size=n, p=[0.55, 0.45])

    base_fare = {1: 80, 2: 25, 3: 12}
    fare = np.array([base_fare[c] for c in pclass]) * RNG.uniform(0.4, 2.2, size=n)
    fare = np.round(fare, 4)

    age = RNG.normal(32, 13, size=n)
    age = np.clip(age, 0.5, 80)
    age_missing_mask = RNG.random(n) < 0.15
    age = np.where(age_missing_mask, np.nan, np.round(age, 1))

    # survival probability loosely correlated with class/sex/age for realism
    surv_prob = 0.15 + (pclass == 1) * 0.35 + (pclass == 2) * 0.15
    surv_prob += (sex == 'female') * 0.35
    surv_prob += np.where(np.isnan(age), 0, (age < 12).astype(float) * 0.2)
    surv_prob = np.clip(surv_prob, 0.03, 0.97)
    survived = (RNG.random(n) < surv_prob).astype(int)

    passenger_id = np.arange(1, n + 1)
    df = pd.DataFrame({
        'passenger_id': passenger_id,
        'pclass': pclass,
        'sex': sex,
        'age': age,
        'fare': fare,
        'survived': survived,
    })
    return df


def gen_t2(n=550):
    signal = RNG.normal(0, 4, size=n)
    signal = np.round(signal, 3)
    # force explicit reset points, including edge cases:
    # - NO reset for the first ~12 rows (tests "count from beginning" when there
    #   is no previous reset at all -- a common off-by-one bug spot)
    # - two consecutive resets
    # - no reset for a long final stretch
    reset_positions = sorted(set(RNG.choice(np.arange(12, n - 40), size=14, replace=False).tolist()))
    for p in reset_positions:
        signal[p] = 0.0
    # consecutive resets edge case
    signal[100] = 0.0
    signal[101] = 0.0
    # guarantee first 12 rows have zero resets (genuine "count from start" prefix)
    signal[:12] = np.where(signal[:12] == 0.0, 0.001, signal[:12])
    df = pd.DataFrame({'timestamp': np.arange(n), 'signal': signal})
    return df


def gen_t3():
    experiments = ['Project Atlas', 'Project Nova', 'Project Orion', 'Project Helios', 'Project Vega']
    rows = []
    for exp in experiments:
        k = RNG.integers(35, 55)
        vals = RNG.normal(50, 10, size=k)
        vals = np.round(vals, 2)
        # scatter missing values, including a leading NaN edge case for one experiment
        miss_mask = RNG.random(k) < 0.18
        vals = vals.astype(float)
        vals[miss_mask] = np.nan
        for v in vals:
            rows.append((exp, v))
    if experiments:
        first_exp_first_idx = next(i for i, r in enumerate(rows) if r[0] == 'Project Vega')
        rows[first_exp_first_idx] = ('Project Vega', np.nan)

    # interleave rows (shuffle order but keep as "transmission order")
    order = RNG.permutation(len(rows))
    rows = [rows[i] for i in order]
    df = pd.DataFrame(rows, columns=['experiment', 'measurement'])
    return df


def gen_t4(width=14, height=11, hazard_p=0.18):
    xs = np.arange(width)
    ys = np.arange(height)
    xx, yy = np.meshgrid(xs, ys)  # x varies fastest within each y row, matching the real input format
    xx = xx.ravel()
    yy = yy.ravel()
    hazard = (RNG.random(len(xx)) < hazard_p).astype(int)
    df = pd.DataFrame({'x': xx, 'y': yy, 'hazard': hazard})
    # guarantee at least one corner hazard and one edge hazard for edge-case coverage
    df.loc[(df.x == 0) & (df.y == 0), 'hazard'] = 1
    df.loc[(df.x == width - 1) & (df.y == 0), 'hazard'] = 1
    return df


def main():
    # Task 1
    t1_in = gen_t1()
    t1_in.to_csv(DATA_DIR / "q1_t1_input.csv", index=False)
    ref.solve_t1(t1_in).to_csv(DATA_DIR / "q1_t1_golden.csv", index=False)

    # Task 2
    t2_in = gen_t2()
    t2_in.to_csv(DATA_DIR / "q1_t2_input.csv", index=False)
    ref.solve_t2(t2_in).to_csv(DATA_DIR / "q1_t2_golden.csv", index=False)

    # Task 3
    t3_in = gen_t3()
    t3_in.to_csv(DATA_DIR / "q1_t3_input.csv", index=False)
    ref.solve_t3(t3_in).to_csv(DATA_DIR / "q1_t3_golden.csv", index=False)

    # Task 4
    t4_in = gen_t4()
    t4_in.to_csv(DATA_DIR / "q1_t4_input.csv", index=False)
    ref.solve_t4(t4_in).to_csv(DATA_DIR / "q1_t4_golden.csv")  # keep index (y)

    print("Generated inputs + golden outputs in", DATA_DIR)


if __name__ == "__main__":
    main()

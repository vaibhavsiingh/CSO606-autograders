import argparse
import math
import random


def make_times(rng, n):
    gaps = [rng.uniform(0.2, 2.5) for _ in range(n - 1)]
    ts = [0.0]
    for g in gaps:
        ts.append(ts[-1] + g)

    # Rescale so the last observation stays within [0, 100].
    scale = rng.uniform(10.0, 100.0) / ts[-1]
    ts = [t * scale for t in ts]
    return ts


def generate(seed=1, impossible=False, noise=0.7):
    rng = random.Random(seed)
    n = rng.randint(5, 100)
    ts = make_times(rng, n)

    if not impossible:
        # Solvable: asteroid stays in front of the station.
        a = rng.uniform(5.0, 25.0)
        b = rng.uniform(0.5, 8.0)
        c = rng.uniform(-0.04, 0.02)

        d = rng.uniform(40.0, 140.0)
        e = rng.uniform(-8.0, -0.5)
        f = rng.uniform(-0.05, 0.01)
    else:
        # Impossible: asteroid stays far to the left, so x < 0 and interception is impossible.
        a = rng.uniform(-60.0, -15.0)
        b = rng.uniform(-10.0, -1.0)
        c = rng.uniform(-0.03, 0.0)

        d = rng.uniform(40.0, 140.0)
        e = rng.uniform(-8.0, -0.5)
        f = rng.uniform(-0.05, 0.01)

    print(n)
    for t in ts:
        x = a + b * t + c * t * t + rng.gauss(0.0, noise)
        y = d + e * t + f * t * t + rng.gauss(0.0, noise)
        print(f"{t:.6f} {x:.6f} {y:.6f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--impossible", action="store_true")
    parser.add_argument("--noise", type=float, default=0.7)
    args = parser.parse_args()
    generate(seed=args.seed, impossible=args.impossible, noise=args.noise)


if __name__ == "__main__":
    main()
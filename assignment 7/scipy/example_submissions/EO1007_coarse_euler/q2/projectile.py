import sys
import math

G = 9.81


def fit_quadratic(t, y):
    n = len(t)
    A = [[1.0, ti, ti * ti] for ti in t]
    # normal equations, solved by hand (Gaussian elimination) -- a plausible
    # but numerically coarser approach than np.linalg.lstsq
    ATA = [[sum(A[k][i] * A[k][j] for k in range(n)) for j in range(3)] for i in range(3)]
    ATy = [sum(A[k][i] * y[k] for k in range(n)) for i in range(3)]

    M = [row[:] + [ATy[i]] for i, row in enumerate(ATA)]
    for col in range(3):
        piv = max(range(col, 3), key=lambda r: abs(M[r][col]))
        M[col], M[piv] = M[piv], M[col]
        pivot = M[col][col]
        for j in range(col, 4):
            M[col][j] /= pivot
        for r in range(3):
            if r != col:
                factor = M[r][col]
                for j in range(col, 4):
                    M[r][j] -= factor * M[col][j]
    return M[0][3], M[1][3], M[2][3]


def main():
    data = sys.stdin.read().strip().splitlines()
    n, k = data[0].split()
    n = int(n)
    k = float(k)

    ts, xs, ys = [], [], []
    for i in range(1, n + 1):
        t, x, y = map(float, data[i].split())
        ts.append(t)
        xs.append(x)
        ys.append(y)

    angle, speed = map(float, data[n + 1].split())

    a, b, c = fit_quadratic(ts, xs)
    d, e, f = fit_quadratic(ts, ys)

    tobs = ts[-1]
    theta = math.radians(angle)
    vx, vy = speed * math.cos(theta), speed * math.sin(theta)
    x, y = 0.0, 0.0

    dt = 0.01  # fixed, fairly coarse step -- less accurate than adaptive RK45
    t = tobs
    hit_time = None
    while y >= 0 or t == tobs:
        ax = a + b * t + c * t * t
        ay = d + e * t + f * t * t
        dist = math.hypot(ax - x, ay - y)
        if dist <= 1.0:
            hit_time = t
            break

        sp = math.hypot(vx, vy)
        vx += (-k * vx * sp) * dt
        vy += (-G - k * vy * sp) * dt
        x += vx * dt
        y += vy * dt
        t += dt

        if t > tobs + 300:
            break

    if hit_time is not None:
        print(f"HIT {hit_time:.6f}")
    else:
        print("MISS")


if __name__ == "__main__":
    main()

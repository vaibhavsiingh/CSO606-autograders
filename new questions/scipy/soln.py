import sys
import math
import numpy as np
from scipy.integrate import solve_ivp

G = 9.81
BLAST_RADIUS = 1.0


def asteroid_fit(t, x, y):
    px = np.polyfit(t, x, 2)
    py = np.polyfit(t, y, 2)
    return px, py


def asteroid_pos(px, py, t):
    return float(np.polyval(px, t)), float(np.polyval(py, t))


def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return

    idx = 0
    N = int(float(data[idx]))
    idx += 1
    K = float(data[idx])
    idx += 1

    t = np.empty(N, dtype=float)
    x = np.empty(N, dtype=float)
    y = np.empty(N, dtype=float)

    for i in range(N):
        t[i] = float(data[idx])
        x[i] = float(data[idx + 1])
        y[i] = float(data[idx + 2])
        idx += 3

    angle_deg = float(data[idx])
    speed = float(data[idx + 1])

    t_obs = float(t[-1])

    px, py = asteroid_fit(t, x, y)

    # Initial asteroid distance check at launch time.
    xa0, ya0 = asteroid_pos(px, py, t_obs)
    if math.hypot(xa0, ya0) <= BLAST_RADIUS:
        print(f"HIT {t_obs:.6f}")
        return

    theta = math.radians(angle_deg)
    vx0 = speed * math.cos(theta)
    vy0 = speed * math.sin(theta)

    state0 = np.array([0.0, 0.0, vx0, vy0], dtype=float)

    def rhs(t_curr, s):
        x_i, y_i, vx, vy = s
        sp = math.hypot(vx, vy)
        ax = -K * vx * sp
        ay = -G - K * vy * sp
        return [vx, vy, ax, ay]

    def hit_event(t_curr, s):
        x_i, y_i = s[0], s[1]
        xa, ya = asteroid_pos(px, py, t_curr)
        return math.hypot(xa - x_i, ya - y_i) - BLAST_RADIUS

    hit_event.terminal = True
    hit_event.direction = -1

    # Integrate in chunks so we can search far enough into the future
    # without relying on one giant solve_ivp call.
    t_curr = t_obs
    t_limit = t_obs + 1000.0
    chunk = 50.0

    while t_curr < t_limit - 1e-12:
        t_next = min(t_curr + chunk, t_limit)

        sol = solve_ivp(
            rhs,
            (t_curr, t_next),
            state0,
            events=hit_event,
            rtol=1e-8,
            atol=1e-10,
            max_step=0.05,
        )

        if sol.t_events and len(sol.t_events[0]) > 0:
            hit_time = float(sol.t_events[0][0])
            print(f"HIT {hit_time:.6f}")
            return

        if not sol.success:
            break

        state0 = sol.y[:, -1]
        t_curr = float(sol.t[-1])

    print("MISS")


if __name__ == "__main__":
    main()
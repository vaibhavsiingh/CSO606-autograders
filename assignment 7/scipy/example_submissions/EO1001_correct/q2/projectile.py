"""
reference_solution.py

Correct model solution for the "Aegis Interceptor" asteroid-defense problem.
Used by generate_tests.py to produce ground-truth expected outputs for every
test case (i.e. this IS the answer key). It is also a valid drop-in
`projectile.py` submission on its own, so it doubles as a "known-good" demo
submission for sanity-testing the grader.

Approach
--------
1. Fit xA(t) = a + b t + c t^2 and yA(t) = d + e t + f t^2 to the noisy
   observations via ordinary least squares (degree-2 polyfit).
2. Integrate the interceptor's ODE system forward from t_obs using
   scipy.integrate.solve_ivp with dense output.
3. Scan the dense solution for the earliest time at which
   ||A(t) - I(t)||_2 <= 1, up until the interceptor returns to the ground
   (y_I <= 0), refining the crossing with a bisection root-find for
   sub-millisecond precision.
"""
import sys
import math
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

G = 9.81
BLAST_RADIUS = 1.0
GROUND_SEARCH_MAX_T = 400.0   # generous cap; physically grounds well before this
COARSE_DT = 0.001             # coarse scan resolution for bracketing roots


def fit_asteroid(t_obs, x_obs, y_obs):
    """Ordinary least-squares quadratic fit for each coordinate independently."""
    t_obs = np.asarray(t_obs, dtype=float)
    x_obs = np.asarray(x_obs, dtype=float)
    y_obs = np.asarray(y_obs, dtype=float)
    # Design matrix [1, t, t^2] -- solved via lstsq (numerically stabler than
    # forming the normal equations by hand for possibly ill-conditioned t).
    A = np.vstack([np.ones_like(t_obs), t_obs, t_obs ** 2]).T
    coeffs_x, *_ = np.linalg.lstsq(A, x_obs, rcond=None)
    coeffs_y, *_ = np.linalg.lstsq(A, y_obs, rcond=None)
    a, b, c = coeffs_x
    d, e, f = coeffs_y
    return a, b, c, d, e, f


def asteroid_pos(coeffs, t):
    a, b, c, d, e, f = coeffs
    t = np.asarray(t, dtype=float)
    x = a + b * t + c * t ** 2
    y = d + e * t + f * t ** 2
    return x, y


def _interceptor_ode(t, state, K):
    x, y, vx, vy = state
    speed = math.hypot(vx, vy)
    return [vx, vy, -K * vx * speed, -G - K * vy * speed]


def simulate_interceptor(tobs, angle_deg, speed, K):
    """Integrate the interceptor ODE from launch until it returns to the ground.

    Returns (sol, ground_time) where `sol` supports dense evaluation via
    sol.sol(t) -> [x, y, vx, vy], valid on [tobs, ground_time].
    """
    theta = math.radians(angle_deg)
    vx0 = speed * math.cos(theta)
    vy0 = speed * math.sin(theta)

    sol = solve_ivp(
        _interceptor_ode,
        [tobs, tobs + GROUND_SEARCH_MAX_T],
        [0.0, 0.0, vx0, vy0],
        args=(K,),
        method="RK45",
        dense_output=True,
        rtol=1e-11,
        atol=1e-13,
        max_step=1.0,
    )

    # Find ground-hit time: first t > tobs where y_I(t) <= 0.
    ts = np.arange(tobs, sol.t[-1], COARSE_DT)
    ts = np.append(ts, sol.t[-1])
    ys = sol.sol(ts)[1]
    # Skip the very first sample (y==0 at launch) when looking for the *return*.
    ground_idx = None
    for i in range(1, len(ts)):
        if ys[i] <= 0.0:
            ground_idx = i
            break
    if ground_idx is None:
        # Never grounded within the search window (shouldn't happen given
        # problem constraints) -- fall back to end of integration.
        ground_time = sol.t[-1]
    else:
        lo, hi = ts[ground_idx - 1], ts[ground_idx]
        if ys[ground_idx - 1] <= 0.0:
            ground_time = lo
        else:
            y_of_t = lambda t: sol.sol(t)[1]
            ground_time = brentq(y_of_t, lo, hi, xtol=1e-10)

    return sol, ground_time


def find_interception(tobs, angle_deg, speed, K, asteroid_coeffs):
    """Returns (hit: bool, time: float or None)."""
    sol, ground_time = simulate_interceptor(tobs, angle_deg, speed, K)
    if ground_time <= tobs:
        return False, None

    ts = np.arange(tobs, ground_time, COARSE_DT)
    ts = np.append(ts, ground_time)

    interceptor_xy = sol.sol(ts)
    ix, iy = interceptor_xy[0], interceptor_xy[1]
    ax, ay = asteroid_pos(asteroid_coeffs, ts)
    dist = np.hypot(ax - ix, ay - iy)

    hit_idx = None
    for i in range(len(ts)):
        if dist[i] <= BLAST_RADIUS:
            hit_idx = i
            break

    if hit_idx is None:
        return False, None

    if hit_idx == 0:
        return True, float(ts[0])

    # Refine the earliest crossing between ts[hit_idx-1] (dist>radius) and
    # ts[hit_idx] (dist<=radius) via bisection on dist(t) - radius.
    lo, hi = ts[hit_idx - 1], ts[hit_idx]

    def gap(t):
        ix_, iy_ = sol.sol(t)[0], sol.sol(t)[1]
        ax_, ay_ = asteroid_pos(asteroid_coeffs, t)
        return math.hypot(ax_ - ix_, ay_ - iy_) - BLAST_RADIUS

    if gap(lo) <= 0:
        hit_time = lo
    else:
        hit_time = brentq(gap, lo, hi, xtol=1e-9)

    return True, float(hit_time)


def solve(input_text):
    """Parse the problem's input format and return the exact output string."""
    lines = [ln for ln in input_text.strip().splitlines()]
    n, k = lines[0].split()
    n = int(n)
    k = float(k)

    t_obs, x_obs, y_obs = [], [], []
    for i in range(1, n + 1):
        ti, xi, yi = lines[i].split()
        t_obs.append(float(ti))
        x_obs.append(float(xi))
        y_obs.append(float(yi))

    angle, speed = lines[n + 1].split()
    angle = float(angle)
    speed = float(speed)

    tobs = t_obs[-1]
    coeffs = fit_asteroid(t_obs, x_obs, y_obs)
    hit, time = find_interception(tobs, angle, speed, k, coeffs)

    if hit:
        return f"HIT {time:.6f}"
    return "MISS"


if __name__ == "__main__":
    data = sys.stdin.read()
    print(solve(data))

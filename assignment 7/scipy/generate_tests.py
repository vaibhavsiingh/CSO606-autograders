"""
generate_tests.py

Builds the hidden-ish test suite for the Aegis Interceptor assignment.

For every scenario:
  1. Pick a "true" asteroid trajectory (a,b,c,d,e,f) and an observation
     schedule (irregular timestamps within some sub-window).
  2. Add Gaussian noise to the observed positions (this noisy data is what
     the student program receives -- exactly matching the problem's
     Input Format).
  3. For HIT-intended scenarios, numerically solve for an (ANGLE, SPEED)
     launch that makes a noiseless interceptor pass through the TRUE
     asteroid position at a chosen target time (inverse ballistics with
     drag, via least-squares). For MISS-intended scenarios, launch
     parameters are picked to clearly not intersect.
  4. The ground truth for grading is NOT the true trajectory -- it is
     whatever reference_solution.solve() produces when fed the exact same
     noisy input a student receives. This is the only fair ground truth,
     since both the reference and any correct student solution are fitting
     the same finite noisy sample with ordinary least squares (a
     deterministic computation), so they must agree to near machine
     precision regardless of how much noise was added.

Each test case is written to tests/<name>/input.txt and tests/<name>/meta.json.
meta.json holds: {expected, weight, category, description, timeout_s}
"""
import hashlib
import json
import math
import os
import shutil

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares

import reference_solution as rs

RNG_SEED = 20260720
TESTS_DIR = os.path.join(os.path.dirname(__file__), "tests")


def _deriv(t, state, K):
    x, y, vx, vy = state
    speed = math.hypot(vx, vy)
    return [vx, vy, -K * vx * speed, -rs.G - K * vy * speed]


def solve_for_launch(asteroid_coeffs, tobs, target_dt, K, guess=(45.0, 150.0)):
    """Find (angle, speed) so a noiseless interceptor is near the asteroid's
    TRUE position at time tobs+target_dt. Returns None if no in-bounds
    solution is found."""
    target_t = tobs + target_dt
    ax, ay = rs.asteroid_pos(asteroid_coeffs, target_t)

    def residual(params):
        angle, speed = params
        theta = math.radians(angle)
        vx0, vy0 = speed * math.cos(theta), speed * math.sin(theta)
        sol = solve_ivp(
            _deriv, [tobs, target_t], [0.0, 0.0, vx0, vy0], args=(K,),
            rtol=1e-10, atol=1e-12, dense_output=False,
        )
        ix, iy = sol.y[0, -1], sol.y[1, -1]
        return [ix - ax, iy - ay]

    result = least_squares(
        residual, x0=list(guess), bounds=([0.0, 1.0], [90.0, 500.0]), xtol=1e-13, ftol=1e-13,
    )
    if not result.success or np.max(np.abs(result.fun)) > 1e-3:
        return None
    angle, speed = result.x
    if not (0.0 <= angle <= 90.0 and 1.0 <= speed <= 500.0):
        return None
    return round(float(angle), 4), round(float(speed), 4)


def make_scenario(rng, n, k, t_window, noise_std, coeff_ranges=None, force_first_t=None):
    """Generate a random true trajectory + noisy observation set."""
    if coeff_ranges is None:
        coeff_ranges = dict(x0=(0, 40), y0=(90, 160), vx=(3, 9), vy=(-14, -3), ax=(-0.4, 0.4), ay=(-0.4, 0.4))
    a = rng.uniform(*coeff_ranges["x0"])
    b = rng.uniform(*coeff_ranges["vx"])
    c = rng.uniform(*coeff_ranges["ax"])
    d = rng.uniform(*coeff_ranges["y0"])
    e = rng.uniform(*coeff_ranges["vy"])
    f = rng.uniform(*coeff_ranges["ay"])
    coeffs = (a, b, c, d, e, f)

    lo, hi = t_window
    t_obs = np.sort(rng.uniform(lo, hi, n))
    # enforce strict monotonicity (t_i < t_{i+1}) even after float rounding
    for i in range(1, n):
        if t_obs[i] <= t_obs[i - 1]:
            t_obs[i] = t_obs[i - 1] + 1e-3

    if force_first_t is not None:
        t_obs[0] = force_first_t
        if t_obs[1] <= t_obs[0]:
            t_obs[1] = t_obs[0] + 1e-3

    x_true, y_true = rs.asteroid_pos(coeffs, t_obs)
    x_obs = x_true + rng.normal(0, noise_std, n)
    y_obs = y_true + rng.normal(0, noise_std, n)
    return coeffs, t_obs, x_obs, y_obs


def format_input(n, k, t_obs, x_obs, y_obs, angle, speed):
    lines = [f"{n} {k}"]
    for t, x, y in zip(t_obs, x_obs, y_obs):
        lines.append(f"{t:.4f} {x:.4f} {y:.4f}")
    lines.append(f"{angle:.4f} {speed:.4f}")
    return "\n".join(lines) + "\n"


def build_case(rng, name, category, description, weight, n, k, t_window,
                noise_std, intent, target_dt=None, angle_speed=None,
                timeout_s=15, coeff_ranges=None, max_attempts=25, force_first_t=None):
    """intent: 'hit' or 'miss'. Retries with fresh randomness until the
    reference solution agrees with the intended outcome."""
    for attempt in range(max_attempts):
        coeffs, t_obs, x_obs, y_obs = make_scenario(rng, n, k, t_window, noise_std, coeff_ranges, force_first_t)
        tobs = t_obs[-1]

        if intent == "hit":
            # Aim at where the *noisy-data fit* (i.e. what the reference
            # solution -- and any correct student solution -- will actually
            # estimate) places the asteroid, not the hidden true trajectory.
            # This is what makes the HIT reproducible from the noisy input
            # alone, matching how grading ground truth is computed below.
            fit_coeffs = rs.fit_asteroid(t_obs, x_obs, y_obs)
            dt = target_dt if target_dt is not None else rng.uniform(2.0, 8.0)
            launch = solve_for_launch(fit_coeffs, tobs, dt, k)
            if launch is None:
                continue
            angle, speed = launch
        else:
            if angle_speed is not None:
                angle, speed = angle_speed
            else:
                angle, speed = rng.uniform(5, 85), rng.uniform(1, 40)

        input_text = format_input(n, k, t_obs, x_obs, y_obs, angle, speed)
        expected = rs.solve(input_text)
        got_hit = expected.startswith("HIT")

        if (intent == "hit" and got_hit) or (intent == "miss" and not got_hit):
            return {
                "name": name,
                "category": category,
                "description": description,
                "weight": weight,
                "timeout_s": timeout_s,
                "expected": expected,
                "input": input_text,
            }
    raise RuntimeError(f"Could not build scenario '{name}' matching intent={intent} after {max_attempts} attempts")


def main():
    if os.path.exists(TESTS_DIR):
        shutil.rmtree(TESTS_DIR)
    os.makedirs(TESTS_DIR)

    master_rng = np.random.default_rng(RNG_SEED)
    cases = []

    def rng_for(tag):
        # Independent, reproducible stream per test name. Python's builtin
        # hash() is salted per-process, so use a stable hash instead.
        digest = hashlib.sha256(tag.encode("utf-8")).hexdigest()
        return np.random.default_rng([RNG_SEED, int(digest[:8], 16)])

    cases.append(build_case(
        rng_for("clean_hit_basic"), "01_clean_hit_basic", "basic",
        "No observation noise; straightforward hit.", 1,
        n=10, k=0.02, t_window=(0, 12), noise_std=0.0, intent="hit"))

    cases.append(build_case(
        rng_for("clean_miss_basic"), "02_clean_miss_basic", "basic",
        "No observation noise; interceptor clearly misses.", 1,
        n=10, k=0.02, t_window=(0, 12), noise_std=0.0, intent="miss"))

    cases.append(build_case(
        rng_for("low_noise_hit"), "03_low_noise_hit", "noise",
        "Light Gaussian noise (std=0.1); should still fit cleanly.", 2,
        n=15, k=0.015, t_window=(0, 15), noise_std=0.1, intent="hit"))

    cases.append(build_case(
        rng_for("low_noise_miss"), "04_low_noise_miss", "noise",
        "Light Gaussian noise (std=0.1); interceptor misses.", 2,
        n=15, k=0.015, t_window=(0, 15), noise_std=0.1, intent="miss"))

    cases.append(build_case(
        rng_for("moderate_noise_hit"), "05_moderate_noise_hit", "noise",
        "Moderate noise (std=0.5) across 20 observations.", 2,
        n=20, k=0.03, t_window=(0, 18), noise_std=0.5, intent="hit"))

    cases.append(build_case(
        rng_for("moderate_noise_miss"), "06_moderate_noise_miss", "noise",
        "Moderate noise (std=0.5); interceptor misses.", 2,
        n=20, k=0.03, t_window=(0, 18), noise_std=0.5, intent="miss"))

    cases.append(build_case(
        rng_for("min_n_hit"), "07_min_n_boundary_hit", "boundary",
        "Minimum allowed N=5 observations.", 2,
        n=5, k=0.02, t_window=(0, 10), noise_std=0.05, intent="hit"))

    cases.append(build_case(
        rng_for("max_n_hit"), "08_max_n_boundary_hit", "boundary",
        "Large N=100 observations (throughput / performance check).", 2,
        n=100, k=0.02, t_window=(0, 40), noise_std=0.3, intent="hit",
        timeout_s=20,
        coeff_ranges=dict(x0=(0, 20), y0=(200, 300), vx=(1, 3), vy=(-2, -0.5), ax=(-0.02, 0.02), ay=(-0.02, 0.02))))

    cases.append(build_case(
        rng_for("high_k_hit"), "09_high_drag_hit", "boundary",
        "High drag coefficient K=0.1 (near upper bound).", 2,
        n=15, k=0.1, t_window=(0, 6), noise_std=0.1, intent="hit",
        target_dt=4.0,
        coeff_ranges=dict(x0=(0, 8), y0=(20, 40), vx=(1, 2), vy=(-2, -0.5), ax=(-0.05, 0.05), ay=(-0.05, 0.05))))

    cases.append(build_case(
        rng_for("low_k_hit"), "10_low_drag_hit", "boundary",
        "Low drag coefficient K=0.001 (near-ballistic).", 2,
        n=15, k=0.001, t_window=(0, 10), noise_std=0.1, intent="hit"))

    cases.append(build_case(
        rng_for("angle_low_miss"), "11_shallow_angle_miss", "edge_launch",
        "Very shallow launch angle; interceptor stays low and misses.", 2,
        n=12, k=0.02, t_window=(0, 12), noise_std=0.1, intent="miss",
        angle_speed=(2.0, 60.0)))

    cases.append(build_case(
        rng_for("angle_high_hit"), "12_steep_angle_hit", "edge_launch",
        "Near-vertical launch angle (close to 90 deg).", 2,
        n=12, k=0.02, t_window=(0, 8), noise_std=0.1, intent="hit",
        coeff_ranges=dict(x0=(0, 5), y0=(90, 160), vx=(0.5, 2.0), vy=(-14, -3), ax=(-0.2, 0.2), ay=(-0.2, 0.2))))

    cases.append(build_case(
        rng_for("speed_min_miss"), "13_min_speed_miss", "edge_launch",
        "Minimum allowed SPEED=1; interceptor barely moves and misses.", 2,
        n=10, k=0.02, t_window=(0, 10), noise_std=0.1, intent="miss",
        angle_speed=(45.0, 1.0)))

    cases.append(build_case(
        rng_for("speed_max_hit"), "14_max_speed_hit", "edge_launch",
        "Maximum allowed SPEED=500.", 2,
        n=12, k=0.02, t_window=(0, 12), noise_std=0.1, intent="hit",
        target_dt=1.5))

    cases.append(build_case(
        rng_for("irregular_ts_hit"), "15_irregular_timestamps_hit", "timing",
        "Highly irregular observation spacing.", 2,
        n=8, k=0.02, t_window=(0, 25), noise_std=0.2, intent="hit"))

    cases.append(build_case(
        rng_for("partial_flight_hit"), "16_partial_flight_extrapolation_hit", "timing",
        "Observations cover only the early flight; large forward extrapolation required.", 2,
        n=8, k=0.02, t_window=(0, 6), noise_std=0.15, intent="hit",
        target_dt=10.0))

    cases.append(build_case(
        rng_for("long_transit_miss"), "17_long_transit_miss", "timing",
        "Asteroid trajectory moves away; no interception ever occurs.", 2,
        n=15, k=0.02, t_window=(0, 20), noise_std=0.2, intent="miss",
        angle_speed=(30.0, 15.0)))

    cases.append(build_case(
        rng_for("stress_noise_hit"), "18_stress_high_noise_hit", "stress",
        "Large N=50 with heavy noise (std=2.0); tests fit robustness.", 3,
        n=50, k=0.025, t_window=(0, 25), noise_std=2.0, intent="hit",
        target_dt=3.0,
        coeff_ranges=dict(x0=(0, 15), y0=(60, 100), vx=(1, 3), vy=(-1, -0.2), ax=(-0.02, 0.02), ay=(-0.02, 0.02))))

    cases.append(build_case(
        rng_for("t0_zero_hit"), "19_first_obs_at_zero_hit", "boundary",
        "First observation exactly at t=0.", 2,
        n=10, k=0.02, t_window=(0, 10), noise_std=0.1, intent="hit",
        force_first_t=0.0))

    cases.append(build_case(
        rng_for("close_call_hit"), "20_close_call_hit", "stress",
        "Interception occurs near the edge of the blast radius (tight timing).", 3,
        n=15, k=0.02, t_window=(0, 12), noise_std=0.05, intent="hit"))

    total_weight = sum(c["weight"] for c in cases)
    manifest = []
    for c in cases:
        case_dir = os.path.join(TESTS_DIR, c["name"])
        os.makedirs(case_dir, exist_ok=True)
        with open(os.path.join(case_dir, "input.txt"), "w") as f:
            f.write(c["input"])
        meta = {k: v for k, v in c.items() if k != "input"}
        with open(os.path.join(case_dir, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2)
        manifest.append(meta)

    with open(os.path.join(TESTS_DIR, "manifest.json"), "w") as f:
        json.dump({"total_weight": total_weight, "cases": manifest}, f, indent=2)

    print(f"Generated {len(cases)} test cases, total weight = {total_weight}")
    for c in cases:
        print(f"  {c['name']:40s} [{c['category']:10s}] expected={c['expected']:>14s} weight={c['weight']}")


if __name__ == "__main__":
    main()

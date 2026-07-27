#!/usr/bin/env python3
"""
Autograder for Q2 - "Multi-container app with Docker Compose" (20 marks)

WHAT THIS DOES
---------------
1. Reads roll_list.csv (column "EO ID") to get the full list of students in the batch.
2. Scans final_submissions/ for student directories, matching each roll number to a
   directory: exact name match first, then a unique substring match as a fallback
   (e.g. roll "21f1000123" matches a folder named "21f1000123_JohnDoe").
3. For every matched submission, grades <roll>/q2/ against the rubric:
      - API Service Requirements      6 marks
      - Tester Service Requirements   6 marks
      - Dockerfile Requirements       2 marks
      - Compose Requirements          6 marks
   using a mix of static file/YAML inspection and an actual
   `docker compose build` / `docker compose up` / log-inspection run.
4. Writes one JSON file per student (grading_output/student_reports/<roll>.json)
   with a full, detailed breakdown for the instructor/TA, plus a short
   "student_comment" summarising only what went wrong.
5. Writes grading_output/grades.csv = original roll_list.csv + two new columns,
   "Marks" and "Comments" (the short student-facing comment).

REQUIREMENTS TO RUN
--------------------
- Python 3.9+, PyYAML  (pip install pyyaml)
- Docker + Docker Compose v2 (the `docker compose` plugin) installed and running.
  This script shells out to the real docker CLI, so it must be run on a machine
  that has Docker available (grading in a sandboxed/offline environment will
  cause every submission to fail the dynamic checks with an "infra_error" -
  use --static-only in that case to grade file structure / Dockerfiles /
  compose YAML only, without marks for actually running the containers).

USAGE
-----
    python3 grader.py \
        --submissions final_submissions \
        --roll-list roll_list.csv \
        --output grading_output

    # to skip actually building/running containers (fast sanity pass, e.g. while
    # testing the grader itself, or when Docker isn't available):
    python3 grader.py --static-only

NOTES / THINGS YOU MAY WANT TO TWEAK
-------------------------------------
- Mark weightings inside each rubric section (MAX_MARKS, and the per-check point
  values inside grade_compose_static / grade_dockerfiles_static /
  grade_api_and_tester) are my best-effort split of the 6/6/2/6 totals given in
  the question. Adjust the constants if you want a different split.
- Comments (both student- and grader-facing) are ONLY generated for things that
  went wrong, per your request - a clean submission gets "All checks passed."
- BUILD_TIMEOUT / UP_TIMEOUT / TESTER_WAIT_TIMEOUT / DOWN_TIMEOUT control how
  long the grader waits on Docker before giving up on a submission - raise
  these if your machine / images are slow.
"""

import argparse
import csv
import json
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML is required. Install with: pip install pyyaml --break-system-packages", file=sys.stderr)
    sys.exit(1)

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

MAX_MARKS = {"api": 6.0, "tester": 6.0, "dockerfiles": 2.0, "compose": 6.0}
TOTAL_MAX = sum(MAX_MARKS.values())  # 20

EXPECTED_TESTER_LINES = [
    "HEALTH=OK",
    "SQUARE=49",
    "REVERSE=esopmoc-rekcod",
    "SUM=42",
    "ALL_TESTS_PASSED",
]

REQUIRED_FILES = [
    "docker-compose.yml",
    "api/Dockerfile",
    "api/server.py",
    "tester/Dockerfile",
    "tester/test_api.py",
]

BUILD_TIMEOUT = 300
UP_TIMEOUT = 120
TESTER_WAIT_TIMEOUT = 120
DOWN_TIMEOUT = 90


class Issue:
    """A single thing that went wrong. `detail` is verbose (for the grader/TA),
    `brief` is a short student-facing line. points_lost is informational only -
    marks are actually computed independently in each grade_* function so that
    a bug in one Issue's bookkeeping can't silently change scores."""

    def __init__(self, category, detail, brief, points_lost=0.0):
        self.category = category
        self.detail = detail
        self.brief = brief
        self.points_lost = round(points_lost, 2)

    def to_dict(self):
        return {
            "category": self.category,
            "detail": self.detail,
            "brief": self.brief,
            "points_lost": self.points_lost,
        }


# --------------------------------------------------------------------------- #
# Roll list / submission matching
# --------------------------------------------------------------------------- #

def load_roll_list(csv_path):
    rows = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if "EO ID" not in reader.fieldnames:
            raise ValueError(
                f"'EO ID' column not found in {csv_path}. Found columns: {reader.fieldnames}"
            )
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
    return rows, fieldnames


def match_submissions(roll_rows, submissions_dir):
    """Match each roll number to a directory inside submissions_dir.

    Preference order: exact directory-name match, then a UNIQUE substring match.
    If a roll number is a substring of more than one directory, that's flagged
    as ambiguous rather than guessed at.
    """
    sub_dir = Path(submissions_dir)
    if not sub_dir.is_dir():
        raise FileNotFoundError(f"Submissions directory not found: {submissions_dir}")

    all_dirs = [d.name for d in sub_dir.iterdir() if d.is_dir()]
    matches = {}
    claimed = {}  # dirname -> roll_no that claimed it

    for row in roll_rows:
        roll = row["EO ID"].strip()
        if not roll:
            continue

        exact = [d for d in all_dirs if d == roll]
        if exact:
            matches[roll] = {"path": sub_dir / exact[0], "match_type": "exact", "note": ""}
            claimed[exact[0]] = roll
            continue

        candidates = [d for d in all_dirs if roll in d]
        if len(candidates) == 1:
            matches[roll] = {
                "path": sub_dir / candidates[0],
                "match_type": "substring",
                "note": f"Matched via substring in directory name '{candidates[0]}'",
            }
            claimed[candidates[0]] = roll
        elif len(candidates) > 1:
            matches[roll] = {
                "path": None,
                "match_type": "ambiguous",
                "note": f"Roll number is a substring of multiple directories: {candidates}. Needs manual resolution.",
            }
        else:
            matches[roll] = {"path": None, "match_type": "missing", "note": "No submission directory found."}

    unclaimed_dirs = [d for d in all_dirs if d not in claimed]
    return matches, unclaimed_dirs


# --------------------------------------------------------------------------- #
# Static checks
# --------------------------------------------------------------------------- #

def find_missing_files(q2_path):
    return [r for r in REQUIRED_FILES if not (q2_path / r).exists()]


def load_compose(q2_path, issues):
    compose_file = q2_path / "docker-compose.yml"
    if not compose_file.exists():
        alt = q2_path / "docker-compose.yaml"
        if alt.exists():
            compose_file = alt
        else:
            return None
    try:
        with open(compose_file) as f:
            return yaml.safe_load(f)
    except Exception as e:  # noqa: BLE001 - want to catch any YAML/parse error
        issues.append(Issue(
            "compose",
            f"Failed to parse {compose_file.name}: {e}",
            "docker-compose.yml could not be parsed (invalid YAML).",
            0,
        ))
        return None


def grade_compose_static(compose_data, issues):
    lost = 0.0
    if compose_data is None or "services" not in (compose_data or {}):
        issues.append(Issue(
            "compose",
            "docker-compose.yml is missing, unparsable, or has no top-level 'services' key.",
            "docker-compose.yml is missing or invalid.",
            MAX_MARKS["compose"],
        ))
        return 0.0

    services = compose_data.get("services") or {}
    api_svc = services.get("api")
    tester_svc = services.get("tester")

    # -- services defined (1 mark) -----------------------------------------
    if api_svc is None or tester_svc is None:
        missing = [n for n, s in [("api", api_svc), ("tester", tester_svc)] if s is None]
        issues.append(Issue(
            "compose",
            f"Missing service definition(s) in docker-compose.yml: {missing}",
            f"Missing service(s) in docker-compose.yml: {', '.join(missing)}",
            1.0,
        ))
        lost += 1.0

    # -- build context correct (1 mark) -------------------------------------
    def build_context_ok(svc, expected_name):
        if not svc:
            return False
        b = svc.get("build")
        ctx = b.get("context") if isinstance(b, dict) else b
        if not ctx:
            return False
        # accept "./api", "api", "q2/api" etc - just require the dir name to appear
        return Path(str(ctx)).name == expected_name

    build_ok = build_context_ok(api_svc, "api") and build_context_ok(tester_svc, "tester")
    if not build_ok:
        issues.append(Issue(
            "compose",
            "One or both services do not build from the correct directory (expected build context './api' for api, './tester' for tester).",
            "Service build context(s) incorrect - should build from ./api and ./tester.",
            1.0,
        ))
        lost += 1.0

    # -- healthcheck defined + sane (2 marks) --------------------------------
    hc = api_svc.get("healthcheck") if api_svc else None
    if not hc:
        issues.append(Issue(
            "compose",
            "api service has no 'healthcheck' key defined.",
            "No healthcheck defined for the api service.",
            2.0,
        ))
        lost += 2.0
    else:
        test = hc.get("test")
        test_str = " ".join(test) if isinstance(test, list) else str(test)
        if "5000" not in test_str or "health" not in test_str.lower():
            issues.append(Issue(
                "compose",
                f"Healthcheck 'test' does not clearly check /health on port 5000. Found: {test_str!r}",
                "Healthcheck does not appear to correctly test the /health endpoint on port 5000.",
                1.0,
            ))
            lost += 1.0

    # -- tester waits on healthy api via depends_on (1 mark) -----------------
    dep_ok = False
    if tester_svc:
        dep = tester_svc.get("depends_on")
        if isinstance(dep, dict) and "api" in dep:
            entry = dep["api"]
            cond = entry.get("condition") if isinstance(entry, dict) else None
            dep_ok = cond == "service_healthy"
    if not dep_ok:
        issues.append(Issue(
            "compose",
            "tester's depends_on for api is missing, or missing 'condition: service_healthy' "
            "(long-form depends_on with a health condition is required - a plain list-form "
            "depends_on only waits for container start, not for the healthcheck).",
            "tester does not correctly wait for api to be healthy (missing 'condition: service_healthy').",
            1.0,
        ))
        lost += 1.0

    # -- private network used, no host networking (1 mark) -------------------
    net_issue = False
    for svc in (api_svc, tester_svc):
        if svc and svc.get("network_mode") == "host":
            net_issue = True
    if net_issue:
        issues.append(Issue(
            "compose",
            "network_mode: host is used by one or more services, bypassing the Compose "
            "private network / service-name DNS resolution the assignment requires.",
            "Uses host networking instead of the Compose private network.",
            1.0,
        ))
        lost += 1.0

    return max(0.0, round(MAX_MARKS["compose"] - lost, 2))


def grade_dockerfiles_static(q2_path, issues):
    lost = 0.0
    per_service_max = MAX_MARKS["dockerfiles"] / 2  # 1 mark each

    for svc, script in [("api", "server.py"), ("tester", "test_api.py")]:
        dpath = q2_path / svc / "Dockerfile"
        if not dpath.exists():
            issues.append(Issue(
                "dockerfiles",
                f"{svc}/Dockerfile is missing.",
                f"{svc}/Dockerfile is missing.",
                per_service_max,
            ))
            lost += per_service_max
            continue

        text = dpath.read_text(errors="ignore")
        sub_lost = 0.0
        third = per_service_max / 3

        if not re.search(r"^\s*FROM\s+python", text, re.MULTILINE | re.IGNORECASE):
            issues.append(Issue(
                "dockerfiles",
                f"{svc}/Dockerfile does not FROM a python base image.",
                f"{svc}/Dockerfile should use a python base image (e.g. python:3.10-slim).",
                third,
            ))
            sub_lost += third

        if not re.search(r"^\s*WORKDIR\s+", text, re.MULTILINE | re.IGNORECASE):
            issues.append(Issue(
                "dockerfiles",
                f"{svc}/Dockerfile does not set WORKDIR.",
                f"{svc}/Dockerfile is missing a WORKDIR instruction.",
                third,
            ))
            sub_lost += third

        if script not in text:
            issues.append(Issue(
                "dockerfiles",
                f"{svc}/Dockerfile does not appear to run {script} in its CMD/ENTRYPOINT.",
                f"{svc}/Dockerfile does not appear to run {script}.",
                third,
            ))
            sub_lost += third

        lost += min(sub_lost, per_service_max)

    return max(0.0, round(MAX_MARKS["dockerfiles"] - lost, 2))


def check_tester_source(q2_path):
    """Returns heuristic notes about how test_api.py talks to the API."""
    notes = {"uses_service_name": False, "hardcodes_localhost": False}
    tpath = q2_path / "tester" / "test_api.py"
    if not tpath.exists():
        return notes
    text = tpath.read_text(errors="ignore")
    if re.search(r"http://api:5000", text):
        notes["uses_service_name"] = True
    if re.search(r"localhost|127\.0\.0\.1", text):
        notes["hardcodes_localhost"] = True
    return notes


# --------------------------------------------------------------------------- #
# Dynamic (actual docker) checks
# --------------------------------------------------------------------------- #

def run_cmd(cmd, cwd, timeout):
    """Run a subprocess, returning (returncode, stdout, stderr, flag).
    flag is None on normal completion, 'timeout' or 'not_found' otherwise."""
    def _as_str(x):
        # subprocess.TimeoutExpired.stdout/.stderr are raw bytes even when
        # text=True was passed to subprocess.run (decoding only happens on
        # normal completion, not on timeout) - normalize everything to str
        # here so no caller ever has to think about it again.
        if x is None:
            return ""
        if isinstance(x, bytes):
            return x.decode("utf-8", errors="replace")
        return x

    try:
        res = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
        return res.returncode, _as_str(res.stdout), _as_str(res.stderr), None
    except subprocess.TimeoutExpired as e:
        return None, _as_str(e.stdout), _as_str(e.stderr), "timeout"
    except FileNotFoundError as e:
        return None, "", str(e), "not_found"


def compose_down(q2_path):
    run_cmd(["docker", "compose", "down", "-v", "--remove-orphans"], q2_path, DOWN_TIMEOUT)


def get_container_name(q2_path, service):
    rc, out, _err, _flag = run_cmd(
        ["docker", "compose", "ps", "-a", "--format", "{{.Name}}", service], q2_path, 30
    )
    if rc == 0 and out.strip():
        return out.strip().splitlines()[0].strip()
    return None


def wait_for_tester_exit(q2_path, timeout=TESTER_WAIT_TIMEOUT):
    start = time.time()
    while time.time() - start < timeout:
        rc, out, _err, _flag = run_cmd(
            ["docker", "compose", "ps", "-a", "--format", "{{.Service}} {{.State}}"], q2_path, 15
        )
        if rc == 0:
            for line in out.strip().splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and parts[0] == "tester" and parts[1] == "exited":
                    return True
        time.sleep(2)
    return False


def get_logs(q2_path, service):
    name = get_container_name(q2_path, service)
    if not name:
        return ""
    rc, out, _err, _flag = run_cmd(["docker", "logs", name], q2_path, 30)
    return out or ""


def run_dynamic(q2_path, issues):
    """Runs docker compose build/up and collects logs. Returns a result dict;
    result['infra_error'] is set if docker itself is unusable on this machine."""
    result = {
        "build_ok": False,
        "up_ok": False,
        "tester_exited": False,
        "tester_exit_code": None,
        "api_logs": "",
        "tester_logs": "",
        "infra_error": None,
    }

    compose_down(q2_path)  # clean slate from any previous run

    rc, out, err, flag = run_cmd(["docker", "compose", "build", "--no-cache"], q2_path, BUILD_TIMEOUT)
    if flag == "not_found":
        result["infra_error"] = "docker executable not found on this machine."
        return result
    if flag == "timeout":
        issues.append(Issue("build", "docker compose build --no-cache timed out.", "Build did not finish in time.", 0))
        return result
    if rc != 0:
        tail = "\n".join((err or out).strip().splitlines()[-25:])
        issues.append(Issue(
            "build",
            f"docker compose build --no-cache failed (exit code {rc}). Last lines of output:\n{tail}",
            "Docker image build failed.",
            0,
        ))
        return result
    result["build_ok"] = True

    rc, out, err, flag = run_cmd(["docker", "compose", "up", "-d"], q2_path, UP_TIMEOUT)
    if flag == "timeout":
        issues.append(Issue(
            "runtime",
            f"docker compose up -d did not finish within {UP_TIMEOUT}s.",
            "Containers took too long to start.",
            0,
        ))
        compose_down(q2_path)
        return result
    if rc != 0:
        tail = "\n".join((err or out).strip().splitlines()[-25:])
        issues.append(Issue(
            "runtime",
            f"docker compose up -d failed (exit code {rc}). Last lines of output:\n{tail}",
            "Containers failed to start.",
            0,
        ))
        compose_down(q2_path)
        return result
    result["up_ok"] = True

    exited = wait_for_tester_exit(q2_path)
    result["tester_exited"] = exited
    if not exited:
        issues.append(Issue(
            "runtime",
            "tester container did not exit within the wait window. Possible causes: api never "
            "became healthy so tester never started, tester hung waiting on a request, or a crash loop.",
            "Tester container never finished running - likely a startup-ordering, networking, or hang issue.",
            0,
        ))

    result["api_logs"] = get_logs(q2_path, "api")
    result["tester_logs"] = get_logs(q2_path, "tester")

    name = get_container_name(q2_path, "tester")
    if name:
        rc, out, _err, _flag = run_cmd(
            ["docker", "inspect", "--format", "{{.State.ExitCode}}", name], q2_path, 15
        )
        if rc == 0:
            try:
                result["tester_exit_code"] = int(out.strip())
            except ValueError:
                pass

    compose_down(q2_path)
    return result


def grade_api_and_tester(dyn_result, tester_src_notes, issues):
    api_marks = 0.0
    tester_marks = 0.0

    if dyn_result is None or dyn_result.get("infra_error") or not dyn_result.get("build_ok"):
        return 0.0, 0.0

    tester_logs = dyn_result.get("tester_logs", "")
    lines = [l.strip() for l in tester_logs.strip().splitlines() if l.strip()]

    # --- API marks (6): 1.5 per endpoint, detected via the tester's own output ---
    endpoint_checks = {
        "HEALTH=OK": ("GET /health", 1.5),
        "SQUARE=49": ("GET /square/7", 1.5),
        "REVERSE=esopmoc-rekcod": ("GET /reverse/docker-compose", 1.5),
        "SUM=42": ("GET /sum?x=13&y=29", 1.5),
    }
    for expected_line, (endpoint_desc, pts) in endpoint_checks.items():
        if expected_line in lines:
            api_marks += pts
        else:
            issues.append(Issue(
                "api",
                f"Expected tester output line '{expected_line}' (for {endpoint_desc}) was not found. "
                f"Full tester log:\n{tester_logs}",
                f"API check failed for {endpoint_desc} - expected output '{expected_line}' was not produced.",
                pts,
            ))

    # --- Tester marks (6) ---
    exact_match = lines[:5] == EXPECTED_TESTER_LINES
    if exact_match:
        tester_marks += 4.0
    else:
        issues.append(Issue(
            "tester",
            f"Tester stdout did not exactly match the required 5 lines in order.\n"
            f"Expected: {EXPECTED_TESTER_LINES}\nGot: {lines}",
            "Tester output did not exactly match the required 5-line format/order.",
            4.0,
        ))

    exit_code = dyn_result.get("tester_exit_code")
    if exit_code == 0 and exact_match:
        tester_marks += 1.0
    else:
        issues.append(Issue(
            "tester",
            f"Tester exit code was {exit_code!r}; expected 0 only when all four endpoint checks "
            "actually passed (and non-zero otherwise).",
            "Tester exit code does not correctly reflect pass/fail status.",
            1.0,
        ))

    if tester_src_notes.get("uses_service_name") and not tester_src_notes.get("hardcodes_localhost"):
        tester_marks += 1.0
    else:
        detail = "tester/test_api.py does not clearly use base URL http://api:5000."
        if tester_src_notes.get("hardcodes_localhost"):
            detail += " It also appears to hardcode localhost/127.0.0.1 somewhere."
        issues.append(Issue(
            "tester",
            detail,
            "Tester script should address the api service by its Compose service name, not localhost/127.0.0.1.",
            1.0,
        ))

    return round(api_marks, 2), round(tester_marks, 2)


# --------------------------------------------------------------------------- #
# Per-student grading orchestration
# --------------------------------------------------------------------------- #

def empty_marks(total=0.0):
    return {"api": 0.0, "tester": 0.0, "dockerfiles": 0.0, "compose": 0.0, "total": total, "max_total": TOTAL_MAX}


def finalize(result, issues, marks):
    brief_msgs = [i.brief for i in issues if i.brief]
    # de-duplicate while preserving order
    student_comment = " | ".join(dict.fromkeys(brief_msgs)) if brief_msgs else "All checks passed."

    if issues:
        grader_comment = "\n\n".join(
            f"[{i.category}] (-{i.points_lost} marks) {i.detail}" for i in issues
        )
    else:
        grader_comment = "No issues found. All static and runtime checks passed."

    result["marks"] = marks
    result["issues"] = [i.to_dict() for i in issues]
    result["student_comment"] = student_comment
    result["grader_comment"] = grader_comment
    return result


def grade_one(roll, submission_path, run_dynamic_checks=True):
    issues = []
    result = {
        "roll_no": roll,
        "submission_dir": str(submission_path) if submission_path else None,
        "found": submission_path is not None,
    }

    if submission_path is None:
        issues.append(Issue(
            "submission", "No submission directory could be matched for this roll number.",
            "No submission found.", TOTAL_MAX,
        ))
        return finalize(result, issues, empty_marks())

    q2_path = submission_path / "q2"
    if not q2_path.is_dir():
        issues.append(Issue(
            "submission", f"'q2' directory not found inside {submission_path}.",
            "Submission is missing the required 'q2' directory.", TOTAL_MAX,
        ))
        return finalize(result, issues, empty_marks())

    missing = find_missing_files(q2_path)
    if missing:
        issues.append(Issue(
            "submission", f"Missing required file(s): {missing}",
            f"Missing required file(s): {', '.join(missing)}", 0,
        ))

    compose_data = load_compose(q2_path, issues)
    compose_marks = grade_compose_static(compose_data, issues)
    dockerfile_marks = grade_dockerfiles_static(q2_path, issues)
    tester_src_notes = check_tester_source(q2_path)

    api_marks = 0.0
    tester_marks = 0.0
    dyn_result = None

    if missing:
        issues.append(Issue(
            "api", "Runtime tests skipped because required files are missing.",
            "Runtime tests skipped - required files missing.", MAX_MARKS["api"],
        ))
        issues.append(Issue(
            "tester", "Runtime tests skipped because required files are missing.",
            "Runtime tests skipped - required files missing.", MAX_MARKS["tester"],
        ))
    elif run_dynamic_checks:
        dyn_result = run_dynamic(q2_path, issues)
        if dyn_result.get("infra_error"):
            issues.append(Issue(
                "infra", dyn_result["infra_error"],
                "Runtime tests could not be executed on the grading machine (Docker unavailable) - "
                "please re-run the grader in an environment with Docker installed.", 0,
            ))
        else:
            api_marks, tester_marks = grade_api_and_tester(dyn_result, tester_src_notes, issues)
    else:
        issues.append(Issue(
            "api", "Runtime tests skipped (--static-only mode).",
            "Runtime (build/run) tests were not performed for this grading pass.", 0,
        ))

    total = round(api_marks + tester_marks + dockerfile_marks + compose_marks, 2)
    marks = {"api": api_marks, "tester": tester_marks, "dockerfiles": dockerfile_marks,
              "compose": compose_marks, "total": total, "max_total": TOTAL_MAX}

    result["dynamic_run"] = {
        "executed": dyn_result is not None,
        "build_ok": dyn_result.get("build_ok") if dyn_result else None,
        "up_ok": dyn_result.get("up_ok") if dyn_result else None,
        "tester_exited": dyn_result.get("tester_exited") if dyn_result else None,
        "tester_exit_code": dyn_result.get("tester_exit_code") if dyn_result else None,
        "api_logs": dyn_result.get("api_logs", "") if dyn_result else "",
        "tester_logs": dyn_result.get("tester_logs", "") if dyn_result else "",
    }

    return finalize(result, issues, marks)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser(description="Autograder for Q2 Docker Compose assignment")
    parser.add_argument("--submissions", default="recheck", help="Path to final_submissions folder")
    parser.add_argument("--roll-list", default="roll_list_temp.csv", help="Path to roll_list.csv")
    parser.add_argument("--output", default="recheck_output", help="Output directory for results")
    parser.add_argument("--static-only", action="store_true",
                         help="Skip docker build/run; grade file structure, Dockerfiles and "
                              "docker-compose.yml only (no marks for api/tester sections).")
    args = parser.parse_args()

    out_dir = Path(args.output)
    json_dir = out_dir / "student_reports"
    json_dir.mkdir(parents=True, exist_ok=True)

    roll_rows, fieldnames = load_roll_list(args.roll_list)
    matches, unclaimed_dirs = match_submissions(roll_rows, args.submissions)

    csv_rows = []
    for row in roll_rows:
        roll = row["EO ID"].strip()
        if not roll:
            continue
        m = matches.get(roll, {"path": None, "match_type": "missing", "note": ""})
        print(f"Grading {roll}  [{m['match_type']}]  {m['path'] or ''}", file=sys.stderr)

        result = grade_one(roll, m["path"], run_dynamic_checks=not args.static_only)
        result["match_type"] = m["match_type"]
        result["match_note"] = m["note"]

        safe_roll = re.sub(r"[^A-Za-z0-9_.-]", "_", roll)
        with open(json_dir / f"{safe_roll}.json", "w") as f:
            json.dump(result, f, indent=2)

        out_row = dict(row)
        out_row["Marks"] = result["marks"]["total"]
        out_row["Comments"] = result["student_comment"]
        csv_rows.append(out_row)

    out_fieldnames = list(fieldnames) + ["Marks", "Comments"]
    with open(out_dir / "grades.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    if unclaimed_dirs:
        with open(out_dir / "unmatched_directories.txt", "w") as f:
            f.write("Directories in final_submissions/ that could not be matched to any roll number in roll_list.csv:\n\n")
            f.write("\n".join(sorted(unclaimed_dirs)))
        print(f"\nWARNING: {len(unclaimed_dirs)} directories in final_submissions/ were not matched "
              f"to any roll number. See {out_dir}/unmatched_directories.txt", file=sys.stderr)

    print(f"\nDone. Per-student JSON reports in {json_dir}/, summary CSV at {out_dir}/grades.csv", file=sys.stderr)


if __name__ == "__main__":
    main()
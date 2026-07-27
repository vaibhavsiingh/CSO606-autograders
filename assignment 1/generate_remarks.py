#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

TASKS: List[Tuple[str, int, str, List[str]]] = [
    ("make_helloworld", 1, "rawmake helloworld", ["make_rc0", "binary_exists", "is_elf", "runs_ok"]),
    ("make_pthread", 2, "rawmake usespthread", ["make_rc0", "binary_exists", "is_elf", "pthread_flag_in_rawmake", "runs_ok"]),
    ("make_static_lib", 2, "rawmake libMyEngineStatic.a", ["make_rc0", "lib_exists", "is_ar_archive", "has_obj_members"]),
    ("make_dynamic_lib", 2, "rawmake libMyEngineDynamic.so", ["make_rc0", "lib_exists", "is_shared_obj"]),
    ("make_mygamestatic", 2, "rawmake mygamestatic", ["make_rc0", "binary_exists", "is_elf", "uses_static_not_dyn", "runs_ok"]),
    ("make_mygamedynamic", 2, "rawmake mygamedynamic", ["make_rc0", "binary_exists", "is_elf", "links_dynamic_lib", "runs_ok"]),
    ("make_clean", 1, "rawmake clean", ["make_rc0", "targets_removed", "no_object_files"]),
    ("cmake_helloworld", 1, "CMake helloworld", ["binary_exists", "is_elf", "runs_ok"]),
    ("cmake_pthread", 2, "CMake usespthread", ["binary_exists", "is_elf", "pthread_flag_in_cmake", "runs_ok"]),
    ("cmake_static_lib", 2, "CMake libMyEngineStatic.a", ["lib_exists", "is_ar_archive", "has_obj_members"]),
    ("cmake_dynamic_lib", 2, "CMake libMyEngineDynamic.so", ["lib_exists", "is_shared_obj"]),
    ("cmake_install", 2, "CMake install", [
        "install_rc0",
        "static_lib_installed",
        "dynamic_lib_installed",
        "header_installed",
        "installed_so_valid",
        "installed_a_valid",
    ]),
    ("cmake_mygamestatic", 2, "CMake mygamestatic", ["binary_exists", "is_elf", "uses_static_not_dyn", "runs_ok"]),
    ("cmake_mygamedynamic", 2, "CMake mygamedynamic", ["binary_exists", "is_elf", "links_dynamic_lib", "runs_ok"]),
]

CHECK_MESSAGES: Dict[str, str] = {
    "make_rc0": "{label} build failed",
    "binary_exists": "{label} output missing",
    "lib_exists": "{label} output missing",
    "is_elf": "{label} output is not an ELF executable",
    "runs_ok": "{label} did not run successfully",
    "pthread_flag_in_rawmake": "rawmake usespthread missing pthread flags",
    "pthread_flag_in_cmake": "CMake usespthread missing pthread linkage",
    "uses_static_not_dyn": "{label} links dynamic library instead of static",
    "links_dynamic_lib": "{label} does not link libMyEngineDynamic",
    "is_shared_obj": "{label} is not a valid shared object",
    "is_ar_archive": "{label} is not a valid static archive",
    "has_obj_members": "{label} missing object files",
    "targets_removed": "rawmake clean did not remove expected targets",
    "no_object_files": "rawmake clean left object files",
    "install_rc0": "CMake install failed",
    "static_lib_installed": "CMake install missing libMyEngineStatic.a",
    "dynamic_lib_installed": "CMake install missing libMyEngineDynamic.so",
    "header_installed": "CMake install missing myengine.hpp",
    "installed_so_valid": "installed libMyEngineDynamic.so is not a valid shared object",
    "installed_a_valid": "installed libMyEngineStatic.a is not a valid static archive",
}

DEFAULT_INPUT_CANDIDATES = [
    Path("final_grading") / "overall-results" / "jsons",
    Path("final_final_grading") / "overall" / "individual_results",
]

TASK_POINTS = {name: points for name, points, _, _ in TASKS}
TASK_LABELS = {name: label for name, _, label, _ in TASKS}
TASK_CHECKS = {name: checks for name, _, _, checks in TASKS}

CMAKE_TASKS = [
    "cmake_helloworld",
    "cmake_pthread",
    "cmake_static_lib",
    "cmake_dynamic_lib",
    "cmake_install",
]

MYGAME_TASKS = [
    "cmake_mygamestatic",
    "cmake_mygamedynamic",
]


def find_candidate_inputs(root: Path) -> List[Path]:
    candidates: List[Path] = []
    for rel in DEFAULT_INPUT_CANDIDATES:
        candidate = root / rel
        if candidate.exists():
            candidates.append(candidate)
    return candidates


def load_report(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def format_points(points: int) -> str:
    return "1 pt" if points == 1 else f"{points} pts"


def render_message(key: str, label: str) -> str:
    template = CHECK_MESSAGES.get(key)
    if template:
        return template.format(label=label)
    return f"{label} failed: {key}"


def task_reasons(task_name: str, task: Dict) -> List[str]:
    checks = task.get("checks")
    if not isinstance(checks, dict):
        return []

    if checks.get("make_rc0") is False:
        return [render_message("make_rc0", TASK_LABELS.get(task_name, task_name))]
    if checks.get("install_rc0") is False:
        return [render_message("install_rc0", TASK_LABELS.get(task_name, task_name))]

    label = TASK_LABELS.get(task_name, task_name)
    reasons: List[str] = []
    for key in TASK_CHECKS.get(task_name, []):
        if checks.get(key) is False:
            reasons.append(render_message(key, label))
    return reasons[:2]


def task_points(task: Dict) -> int:
    points = task.get("points")
    if isinstance(points, int):
        return points
    return 0


def task_skipped(task: Dict) -> bool:
    return bool(task.get("skipped"))


def skipped_group_remarks(report: Dict) -> Tuple[List[str], List[str]]:
    remarks: List[str] = []
    skipped_tasks: List[str] = []

    cmake_skipped = [name for name in CMAKE_TASKS if task_skipped(report.get(name, {}))]
    if cmake_skipped:
        lost = sum(TASK_POINTS[name] for name in cmake_skipped)
        cmake_setup = report.get("cmake_setup", {})
        if cmake_setup.get("returncode") not in (0, None):
            remarks.append(f"CMake build failed; CMake tasks skipped (lost {format_points(lost)})")
        else:
            remarks.append(f"CMake tasks skipped (lost {format_points(lost)})")
        skipped_tasks.extend(cmake_skipped)

    mygame_skipped = [name for name in MYGAME_TASKS if task_skipped(report.get(name, {}))]
    if mygame_skipped:
        lost = sum(TASK_POINTS[name] for name in mygame_skipped)
        mygame_setup = report.get("mygame_cmake_setup", {})
        if mygame_setup.get("returncode") not in (0, None):
            remarks.append(f"Mygame CMake build failed; mygame tasks skipped (lost {format_points(lost)})")
        else:
            remarks.append(f"Mygame CMake tasks skipped (lost {format_points(lost)})")
        skipped_tasks.extend(mygame_skipped)

    return remarks, skipped_tasks


def build_remarks(report: Dict) -> Tuple[str, int]:
    if report.get("error"):
        return "Submission extraction failed; not graded (lost 25 pts)", 0

    remarks: List[str] = []
    skipped_remarks, skipped_tasks = skipped_group_remarks(report)
    remarks.extend(skipped_remarks)

    total = report.get("total")
    if not isinstance(total, int):
        total = 0
        for name, max_points, _, _ in TASKS:
            total += task_points(report.get(name, {}))

    for task_name, max_points, label, _ in TASKS:
        if task_name in skipped_tasks:
            continue
        task = report.get(task_name)
        if not isinstance(task, dict):
            continue
        earned = task_points(task)
        if earned >= max_points:
            continue
        lost = max_points - earned
        reasons = task_reasons(task_name, task)
        if not reasons:
            reasons = [f"{label} did not pass all checks"]
        for reason in reasons:
            remarks.append(f"{reason} (lost {format_points(lost)})")
            break

    if not remarks:
        remarks.append("No deductions")

    return "; ".join(remarks), total


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate remarks from grading JSON files.")
    parser.add_argument("--input", type=str, help="Folder with per-student JSON files")
    parser.add_argument("--output", type=str, help="Output CSV path")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    if args.input:
        input_dir = Path(args.input)
    else:
        candidates = find_candidate_inputs(root)
        if not candidates:
            print("Error: input directory not found. Use --input to specify it.")
            return 2
        if len(candidates) > 1:
            print("Error: multiple input folders found. Please pick one with --input:")
            for candidate in candidates:
                print(f"  - {candidate}")
            return 2
        input_dir = candidates[0]

    if not input_dir.exists():
        print("Error: input directory not found. Use --input to specify it.")
        return 2

    json_files = sorted(p for p in input_dir.iterdir() if p.is_file() and p.suffix == ".json")
    if not json_files:
        print(f"Error: no .json files found in {input_dir}")
        return 2

    output_path = Path(args.output) if args.output else input_dir.parent / "remarks.csv"

    rows: List[Tuple[str, int, str]] = []
    for path in json_files:
        report = load_report(path)
        student_id = report.get("student_id") or path.stem
        remarks, total = build_remarks(report)
        rows.append((student_id, total, remarks))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["student_id", "total", "remarks"])
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile

TEST_CASES_DIR = Path('organise_grading_testcases')
ORGANISE_SCRIPT = Path('evaluate_grading_testcases') / 'organise.sh'
EXPECTED_DIR = Path('evaluate_grading_testcases') / 'expected'
RUN_TIMEOUT = 5


def list_testcases(testcases_dir: Path) -> list[Path]:
    cases = sorted([p for p in testcases_dir.iterdir() if p.is_dir()])
    if not cases:
        raise FileNotFoundError(f'No testcases found in {testcases_dir}')
    return cases


def read_roll_list(mock_dir: Path) -> list[str]:
    roll_list = mock_dir / 'roll_list'
    return [line.strip() for line in roll_list.read_text().splitlines() if line.strip()]


def input_sort_key(path: Path) -> tuple[int, object]:
    stem = path.stem
    try:
        return (0, int(stem))
    except ValueError:
        return (1, stem)


def collect_testcases(mock_dir: Path) -> list[tuple[str, Path, Path]]:
    inputs_dir = mock_dir / 'inputs'
    outputs_dir = mock_dir / 'outputs'
    input_files = [p for p in inputs_dir.iterdir() if p.is_file()]
    output_files = {p.stem: p for p in outputs_dir.iterdir() if p.is_file()}

    testcases: list[tuple[str, Path, Path]] = []
    for inp in sorted(input_files, key=input_sort_key):
        out = output_files.get(inp.stem)
        if out is None:
            alt = outputs_dir / inp.name
            if alt.exists():
                out = alt
        if out is None:
            continue
        testcases.append((inp.stem, inp, out))

    return testcases


def compile_cpp(cpp_path: Path, cwd: Path) -> Path | None:
    exe_base = cwd / 'executable'
    exe_win = exe_base.with_suffix('.exe')
    if exe_base.exists():
        exe_base.unlink()
    if exe_win.exists():
        exe_win.unlink()

    try:
        result = subprocess.run(
            ['g++', cpp_path.name, '-o', exe_base.name],
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return None

    if result.returncode != 0:
        return None

    if exe_base.exists():
        return exe_base
    if exe_win.exists():
        return exe_win
    return None


def write_student_output(
    exe_path: Path | None,
    cwd: Path,
    input_path: Path,
    output_path: Path,
) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if exe_path is None:
        output_path.write_bytes(b'')
        return False

    with input_path.open('rb') as fin, output_path.open('wb') as fout:
        try:
            subprocess.run(
                [str(exe_path)],
                cwd=cwd,
                stdin=fin,
                stdout=fout,
                stderr=subprocess.DEVNULL,
                timeout=RUN_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return False
    return True


def setup_temp_case(testcase: Path, temp_dir: Path) -> None:
    shutil.copytree(testcase, temp_dir / 'mock_grading')
    shutil.copy(ORGANISE_SCRIPT, temp_dir / 'organise.sh')
    result = subprocess.run(
        ['bash', 'organise.sh'],
        cwd=temp_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        suffix = f' ({details[:200]})' if details else ''
        raise RuntimeError(f'organise.sh failed{suffix}')


def compute_expected_results(base_dir: Path) -> tuple[list[str], dict[str, int], dict[str, int], list[str]]:
    mock_dir = base_dir / 'mock_grading'
    organised_dir = base_dir / 'organised'
    roll_list = read_roll_list(mock_dir)
    testcases = collect_testcases(mock_dir)
    distribution = {test_id: 0 for test_id, _, _ in testcases}
    scores: dict[str, int] = {roll: 0 for roll in roll_list}

    for roll in roll_list:
        roll_dir = organised_dir / roll
        if not roll_dir.is_dir():
            continue

        cpp_files = sorted(
            [p for p in roll_dir.iterdir() if p.is_file() and p.suffix == '.cpp']
        )
        exe_path = compile_cpp(cpp_files[0], roll_dir) if cpp_files else None

        score = 0
        student_outputs = roll_dir / 'student_outputs'
        for test_id, inp, out in testcases:
            output_path = student_outputs / out.name
            ran = write_student_output(exe_path, roll_dir, inp, output_path)
            if ran and output_path.read_bytes() == out.read_bytes():
                score += 1
                distribution[test_id] += 1
        scores[roll] = score

    test_ids = [test_id for test_id, _, _ in testcases]
    return roll_list, scores, distribution, test_ids


def write_expected_files(
    testcase: Path,
    roll_list: list[str],
    scores: dict[str, int],
    distribution: dict[str, int],
    test_ids: list[str],
) -> None:
    expected_dir = EXPECTED_DIR / testcase.name
    expected_dir.mkdir(parents=True, exist_ok=True)

    marksheet_lines = [f"{roll},{scores.get(roll, 0)}" for roll in sorted(roll_list)]
    marksheet_path = expected_dir / 'marksheet.csv'
    marksheet_path.write_text("\n".join(marksheet_lines) + ("\n" if marksheet_lines else ""))

    dist_lines = [f"{test_id},{distribution.get(test_id, 0)}" for test_id in test_ids]
    distribution_path = expected_dir / 'distribution.txt'
    distribution_path.write_text("\n".join(dist_lines) + ("\n" if dist_lines else ""))


def main() -> int:
    try:
        testcases = list_testcases(TEST_CASES_DIR)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    for testcase in testcases:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            try:
                setup_temp_case(testcase, tmp_path)
                roll_list, scores, distribution, test_ids = compute_expected_results(tmp_path)
                write_expected_files(testcase, roll_list, scores, distribution, test_ids)
                print(f"Wrote expected files for {testcase.name}")
            except Exception as exc:
                print(f"ERROR: {testcase.name}: {exc}")
                return 1

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

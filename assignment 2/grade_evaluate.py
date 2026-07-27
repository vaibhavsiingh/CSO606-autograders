"""
Rubric
------
 4  marksheet.csv is created with the correct number of lines (one per student)
 4  marksheet.csv is sorted in lexicographic order of roll numbers
 5  marksheet.csv contains correct scores for students whose code compiles & runs
 4  distribution.txt is created with the correct number of lines (one per test input)
 4  distribution.txt contains correct per-input correct-submission counts
 4  student_outputs/ directories are created correctly for each roll number
----
25

Assumption: testcases are available under organise_grading_testcases/.
We iterate over all testcases, copy each into workDir as mock_grading,
then run evaluate_grading_testcases/organise.sh to build organised/.
"""

from pathlib import Path
import shutil, subprocess, sys
from grader_utils import (
    submissions_dir, work_dir,
    refresh_workdir, copy_script, append_grade,
)

GRADE_CSV        = 'grade-evaluate.csv'
BASH_SCRIPT_NAME = 'evaluate.sh'
TOTAL_MARKS      = 25
TEST_CASES_DIR   = Path('organise_grading_testcases')
EVALUATE_ORGANISE_SCRIPT = Path('evaluate_grading_testcases') / 'organise.sh'
TESTCASE_WEIGHTS = [0.25, 0.35, 0.40]
EXPECTED_DIR     = Path('evaluate_grading_testcases') / 'expected'



def list_testcases(testcases_dir: Path) -> list[Path]:
    cases = sorted([p for p in testcases_dir.iterdir() if p.is_dir()])
    if not cases:
        raise FileNotFoundError(f'No testcases found in {testcases_dir}')
    return cases


def setup_workdir(wd: Path, testcase: Path) -> tuple[bool, str]:
    shutil.copytree(testcase, wd / 'mock_grading')

    try:
        shutil.copy(EVALUATE_ORGANISE_SCRIPT, wd / 'organise.sh')
    except FileNotFoundError:
        return False, f'GRADER ERROR: {EVALUATE_ORGANISE_SCRIPT} missing'

    try:
        result = subprocess.run(
            ['bash', 'organise.sh'],
            cwd=wd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return False, 'GRADER ERROR: organise.sh timed out'

    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        suffix = f' ({details[:200]})' if details else ''
        return False, f'GRADER ERROR: organise.sh failed{suffix}'

    return True, ''


def read_roll_list(mock_dir: Path) -> list[str]:
    roll_list = mock_dir / 'roll_list'
    return [line.strip() for line in roll_list.read_text().splitlines() if line.strip()]




# ── checks ────────────────────────────────────────────────────────────────────

def parse_marksheet(path: Path) -> dict[str, int]:
    """Return {roll: score} from marksheet.csv."""
    scores = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(',')
        if len(parts) >= 2:
            try:
                scores[parts[0].strip()] = int(parts[1].strip())
            except ValueError:
                continue
    return scores


def parse_distribution(path: Path) -> dict[str, int]:
    """Return {test_id: count} from distribution.txt."""
    counts: dict[str, int] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        # format: "0, 6"  or  "0,6"
        parts = line.split(',')
        if len(parts) >= 2:
            test_id = parts[0].strip()
            try:
                counts[test_id] = int(parts[1].strip())
            except ValueError:
                continue
    return counts


def read_nonempty_lines(path: Path) -> list[str]:
    return [line for line in path.read_text().splitlines() if line.strip()]


def expected_paths_for_testcase(testcase: Path) -> tuple[Path, Path]:
    expected_dir = EXPECTED_DIR / testcase.name
    return expected_dir / 'marksheet.csv', expected_dir / 'distribution.txt'


def load_expected_for_testcase(testcase: Path) -> tuple[dict[str, int], dict[str, int], int]:
    marksheet_path, distribution_path = expected_paths_for_testcase(testcase)
    if not marksheet_path.exists():
        raise FileNotFoundError(f'missing expected marksheet: {marksheet_path}')
    if not distribution_path.exists():
        raise FileNotFoundError(f'missing expected distribution: {distribution_path}')

    expected_scores = parse_marksheet(marksheet_path)
    expected_distribution = parse_distribution(distribution_path)
    dist_line_count = len(read_nonempty_lines(distribution_path))
    return expected_scores, expected_distribution, dist_line_count


def check_results(
    wd: Path,
    roll_list: list[str],
    expected_scores: dict[str, int],
    expected_distribution: dict[str, int],
    expected_dist_line_count: int,
) -> tuple[int, list[str]]:
    marks   = 0
    remarks = []

    marksheet    = wd / 'marksheet.csv'
    distribution = wd / 'distribution.txt'

    # ── marksheet.csv ─────────────────────────────────────────────────────────
    if not marksheet.exists():
        remarks.append('FAIL: marksheet.csv not created')
    else:
        lines = [l for l in marksheet.read_text().splitlines() if l.strip()]

        # (a) correct number of lines (4 marks)
        if len(lines) == len(roll_list):
            marks += 4
        else:
            remarks.append(f'FAIL: marksheet.csv has {len(lines)} lines, expected {len(roll_list)}')

        # (b) sorted in lexicographic order (4 marks)
        roll_col = [l.split(',')[0].strip() for l in lines]
        if roll_col == sorted(roll_col):
            marks += 4
        else:
            remarks.append(f'FAIL: marksheet.csv not sorted: {roll_col}')

        # (c) correct scores (5 marks)
        scores       = parse_marksheet(marksheet)
        correct_count = sum(1 for roll, exp in expected_scores.items()
                            if scores.get(roll) == exp)
        score_frac = correct_count / len(expected_scores)
        score_marks = round(5 * score_frac)
        marks += score_marks
        if score_marks != 5:
            wrong = {r: (scores.get(r), e) for r, e in expected_scores.items()
                     if scores.get(r) != e}
            remarks.append(f'PARTIAL ({score_marks}/5): wrong scores: got/expected {wrong}')

    # ── distribution.txt ──────────────────────────────────────────────────────
    if not distribution.exists():
        remarks.append('FAIL: distribution.txt not created')
    else:
        dist_lines = [l for l in distribution.read_text().splitlines() if l.strip()]

        # (d) correct number of lines (4 marks)
        if len(dist_lines) == expected_dist_line_count:
            marks += 4
        else:
            remarks.append(
                f'FAIL: distribution.txt has {len(dist_lines)} lines, expected {expected_dist_line_count}'
            )

        # (e) correct counts (4 marks)
        dist = parse_distribution(distribution)
        if dist == expected_distribution:
            marks += 4
        else:
            remarks.append(f'FAIL: distribution.txt got {dist}, expected {expected_distribution}')

    # ── student_outputs/ directories ──────────────────────────────────────────
    organised = wd / 'organised'
    # (f) student_outputs exist for every roll (4 marks)
    missing_outputs = []
    for roll in roll_list:
        so = organised / roll / 'student_outputs'
        if not so.is_dir():
            missing_outputs.append(roll)
    if not missing_outputs:
        marks += 4
    else:
        frac = 1 - len(missing_outputs) / len(roll_list)
        marks += round(4 * frac)
        remarks.append(f'PARTIAL: student_outputs/ missing for {missing_outputs}')

    return marks, remarks


# ── per-student driver ────────────────────────────────────────────────────────

def grade_student(student_dir: Path) -> tuple[int, str]:
    try:
        testcases = list_testcases(TEST_CASES_DIR)
    except Exception as exc:
        return 0, f'GRADER ERROR: {exc}'

    if len(testcases) != len(TESTCASE_WEIGHTS):
        return 0, 'GRADER ERROR: testcase/weight count mismatch'

    total_marks = 0.0
    total_remarks = []

    for index, testcase in enumerate(testcases):
        weight = TESTCASE_WEIGHTS[index]
        refresh_workdir()

        ok, setup_msg = setup_workdir(work_dir, testcase)
        if not ok:
            return 0, setup_msg

        try:
            roll_list = read_roll_list(work_dir / 'mock_grading')
            expected_scores, expected_distribution, expected_dist_line_count = load_expected_for_testcase(testcase)
        except Exception as exc:
            return 0, f'GRADER ERROR: {exc}'

        if not copy_script(student_dir, BASH_SCRIPT_NAME):
            return 0, 'evaluate.sh not found in submission'

        try:
            result = subprocess.run(
                ['bash', BASH_SCRIPT_NAME],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return 0, 'TIMEOUT: evaluate.sh took too long'

        marks, remarks = check_results(
            work_dir,
            roll_list,
            expected_scores,
            expected_distribution,
            expected_dist_line_count,
        )
        total_marks += marks * weight
        total_remarks += remarks

    return min(total_marks, TOTAL_MARKS), ' | '.join(total_remarks)


# ── main ──────────────────────────────────────────────────────────────────────

def parse_start_from(argv: list[str]) -> str | None:
    if not argv:
        return None
    if argv[0] in ('-s', '--start') and len(argv) > 1:
        return argv[1]
    if argv[0].startswith('--start='):
        return argv[0].split('=', 1)[1]
    return argv[0]


def normalize_id(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().lower()


def resolve_start_from() -> str | None:
    start_from = parse_start_from(sys.argv[1:])
    if start_from is None and sys.stdin.isatty():
        start_from = input('Start from roll (leave blank for all): ').strip() or None
    return start_from

def main():
    start_from = normalize_id(resolve_start_from())
    grade_csv = Path(GRADE_CSV)
    if grade_csv.exists() and start_from is None:
        grade_csv.unlink()
    started = start_from is None
    found_start = start_from is None

    for student_dir in sorted(submissions_dir.iterdir()):
        student_id = student_dir.name
        student_key = normalize_id(student_id)

        if not started:
            if student_key == start_from:
                started = True
                found_start = True
            else:
                continue

        print(f'Grading {student_id} …', end=' ', flush=True)

        marks, remarks = grade_student(student_dir)
        append_grade(grade_csv, student_id, marks, remarks)
        print(f'{marks}/{TOTAL_MARKS}  –  {remarks}')

    if start_from and not found_start:
        print(f'NOTE: start roll not found: {start_from}')

    print(f'\nDone. Results in {GRADE_CSV}')


if __name__ == '__main__':
    main()
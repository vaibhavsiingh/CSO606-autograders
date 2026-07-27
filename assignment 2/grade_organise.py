"""

Rubric
------
 4  organised/ directory is created at the correct level
 4  A subdirectory exists for EVERY roll number in roll_list (no extras, no missing)
 6  Every submission file appears as a symbolic link inside the correct roll dir
 6  All symbolic links use RELATIVE paths (not absolute)
----
20
"""

from pathlib import Path
import shutil, os
from grader_utils import (
    submissions_dir, work_dir,
    refresh_workdir, copy_script, append_grade,
)

GRADE_CSV        = 'grade-organise.csv'
BASH_SCRIPT_NAME = 'organise.sh'
TOTAL_MARKS      = 20
TEST_CASES_DIR   = 'organise_grading_testcases'
TESTCASE_WEIGHTS = [0.25, 0.35, 0.40]




def check_organised(wd: Path) -> tuple[int, list[str]]:
    marks   = 0
    remarks = []
    organised = wd / 'organised'
    
    if not organised.is_dir():
        remarks.append('FAIL: organised/ directory not created')
        return marks, remarks
    marks += 4

    
    roll_list_path = wd / 'mock_grading' / 'roll_list'
    expected_rolls = set(roll_list_path.read_text().split())
    found_rolls = {
        p.name.rstrip('\r')
        for p in organised.iterdir()
        if p.is_dir()
    }

    missing_rolls = expected_rolls - found_rolls
    extra_rolls   = found_rolls - expected_rolls

    if not missing_rolls and not extra_rolls:
        marks += 4
    elif not missing_rolls:
        marks += 2
        remarks.append(f'PARTIAL: all rolls present but extra dirs: {sorted(extra_rolls)}')
    elif not extra_rolls:
        marks += 2
        remarks.append(f'PARTIAL: correct dirs only but missing rolls: {sorted(missing_rolls)}')
    else:
        remarks.append(f'FAIL: missing {sorted(missing_rolls)}, extra {sorted(extra_rolls)}')

    
    # Build expected mapping: roll -> list of filenames
    expected_links: dict[str, list[str]] = {r: [] for r in expected_rolls}
    mock_grading_subs = wd / "mock_grading" / "submissions"
    for file in mock_grading_subs.iterdir():
        # roll number = first N chars where N = len of any roll number
        if file.is_file():
            fname = file.name
            roll_len = len(next(iter(expected_rolls)))
            roll = fname[:roll_len]
            if roll in expected_links:
                expected_links[roll].append(fname)

    link_marks    = 0
    link_max      = 6
    relpath_marks = 0
    relpath_max   = 6
    total_files = sum(len(v) for v in expected_links.values())    
    if total_files == 0:
        return marks, remarks

    per_file_link    = link_max    / total_files
    per_file_relpath = relpath_max / total_files
    
    for roll, files in expected_links.items():        
        roll_dir = organised / roll
        if not roll_dir.is_dir():            
            continue
        for fname in files:
            link_path = roll_dir / fname
            if not link_path.exists() and not link_path.is_symlink():
                remarks.append(f'FAIL: symlink missing: {roll}/{fname}')
                continue

            if link_path.is_symlink():
                target = os.readlink(link_path)
                expected_target = (wd / 'mock_grading' / 'submissions' / fname).resolve()
                if os.path.isabs(target):
                    resolved_target = Path(target).resolve()
                    remarks.append(f'FAIL: absolute symlink for {roll}/{fname}: {target}')
                else:
                    resolved_target = (roll_dir / target).resolve()
                    relpath_marks += per_file_relpath

                if resolved_target == expected_target:
                    link_marks += per_file_link
                else:
                    remarks.append(f'FAIL: symlink target incorrect for {roll}/{fname}: {target}')
            else:
                # It's a real file copy, not a symlink – deduct symlink marks
                remarks.append(f'FAIL: {roll}/{fname} exists but is NOT a symlink')

    marks += round(link_marks,2)
    marks += round(relpath_marks,2)

    return marks, remarks



def grade_student(student_dir: Path) -> tuple[int, str]:


    test_case_dir = Path(TEST_CASES_DIR)
    testcases = sorted([p for p in test_case_dir.iterdir() if p.is_dir()])
    if len(testcases) != len(TESTCASE_WEIGHTS):
        return 0, 'GRADER ERROR: testcase/weight count mismatch'

    total_marks = 0.0
    total_remarks = []

    for index, testcase in enumerate(testcases):        
        weight = TESTCASE_WEIGHTS[index]
        refresh_workdir()
        shutil.copytree(testcase, work_dir / "mock_grading")
        

        if not copy_script(student_dir, BASH_SCRIPT_NAME):
            return 0, 'organise.sh not found in submission'

        try:
            import subprocess
            result = subprocess.run(
                ['bash', BASH_SCRIPT_NAME],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return 0, 'TIMEOUT: organise.sh took too long'

        if result.returncode != 0:
            pass 

        marks, remarks = check_organised(work_dir)
        total_marks   += marks * weight
        total_remarks += remarks

    return min(total_marks, TOTAL_MARKS), ' | '.join(total_remarks)


def main():
    grade_csv = Path(GRADE_CSV)
    if grade_csv.exists():
        grade_csv.unlink()

    for student_dir in sorted(submissions_dir.iterdir()):
        student_id = student_dir.name
        print(f'Grading {student_id} …', end=' ', flush=True)

        marks, remarks = grade_student(student_dir)
        
        append_grade(grade_csv, student_id, marks, remarks)
        print(f'{marks}/{TOTAL_MARKS}  -  {remarks}')
        

    print(f'\nDone. Results in {GRADE_CSV}')


if __name__ == '__main__':
    main()
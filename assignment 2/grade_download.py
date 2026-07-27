"""
At grading time the student's download.sh is run, and the resulting
mock_grading/ is diffed against STANDARD_DIR with three checks:

  2 marks  :  mock_grading/ is the only new item in work_dir (no host dirs, no junk)
  6 marks  :  exact same set of files & directories (relative paths match the correct answer)
     otherwise deductions based on:
      - missing expected files
      - unexpected extra files
    if mock_grading/ itself is missing but expected files are found elsewhere,
    partial marks are awarded
  1 mark   :  no stdout/stderr by the script
  1 mark   :  local directory is called mock_grading
  
 ──────────
 10 marks
"""

from pathlib import Path
import subprocess, shutil, sys
from grader_utils import (
    submissions_dir, work_dir,
    refresh_workdir, copy_script, append_grade,
)

GRADE_CSV        = 'grade-download.csv'
BASH_SCRIPT_NAME = 'download.sh'
TOTAL_MARKS      = 10

# Where the reference copy lives (relative to this script's directory)
STANDARD_DIR_TC01 = Path('download_grading_testcases') / 'download_grading_standard_tc01' 
STANDARD_DIR_TC02 = Path('download_grading_testcases') / 'download_grading_standard_tc02' 
STANDARD_DIR_TC03 = Path('download_grading_testcases') / 'download_grading_standard_tc03' 

WEBSITE_TESTCASES = [
    ('https://www.cse.iitb.ac.in/~as/bash-assignment/mock-grading/', 2),
    ('http://localhost:8000/website/one_more_level/hehe_one_more_lvl/last_one/i_lied/folder_that_is_not_mock_grading/', 5),
    ('http://localhost:8001/not_mock_grading/', 0)
]

TESTCASE_WEIGHTS = [0.25, 0.35, 0.40]



def relative_paths(base: Path) -> set[str]:    
    return {str(p.relative_to(base)) for p in base.rglob('*')}


def check_no_output(result: subprocess.CompletedProcess) -> tuple[int, str]:        
    if not result.stdout.strip() and not result.stderr.strip():
        return 1, ''
    details = []
    marks = 1.0
    if result.stdout.strip():
        marks -= 0.5
        details.append(f'stdout: {result.stdout.strip()[:120]!r}')
    if result.stderr.strip():
        marks -= 0.5
        details.append(f'stderr: {result.stderr.strip()[:120]!r}')
    output_str = "; ".join(details)
    if len(output_str) > 200:
        output_str = output_str[:197] + '...'
    return marks, f'FAIL: script produced output-> {output_str}'


def check_named_mock_grading(wd: Path) -> tuple[int, str]:    
    if (wd / 'mock_grading').is_dir():
        return 1, ''
    
    other_dirs = [p.name for p in wd.iterdir()
                  if p.is_dir() and p.name != BASH_SCRIPT_NAME]
    if other_dirs:
        return 0, f'FAIL: directory not named mock_grading (found: {other_dirs})'
    return 0, 'FAIL: no downloaded directory found at all'


def check_only_mock_grading(wd: Path) -> tuple[int, str]:    
    extra = [p.name for p in wd.iterdir()
             if p.name not in (BASH_SCRIPT_NAME, 'mock_grading')]
    if not extra:
        return 2, ''
    return 0, f'FAIL: unexpected items in work_dir: {extra}'


def check_file_structure(wd: Path, standard: Path) -> tuple[float, str]:
    
    mock = wd / 'mock_grading'
    standard_mock = standard / "mock_grading"

    if not mock.is_dir():
         # maybe they downloaded correct files but wrong top-level folder
        student_filenames = {
            p.name for p in wd.rglob('*')
            if p.is_file()
        }

        standard_filenames = {
            p.name for p in standard_mock.rglob('*')
            if p.is_file()
        }

        common = student_filenames & standard_filenames

        if common:
            return len(common) * 3 / len(standard_filenames), (
                'mock_grading/ missing, but some expected files found: '
                f'{sorted(common)}'
            )

        return 0, 'FAIL: mock_grading/ does not exist and no expected files found'
       

    student_paths = relative_paths(mock)
    standard_paths  = relative_paths(standard_mock)
    
    if student_paths == standard_paths:
        return 6, ''

    deduction = 0
    remarks   = []

    
    standard_filenames = {
        p.name for p in standard_mock.rglob('*')
        if p.is_file()
    }

    student_filenames = {
        p.name for p in mock.rglob('*')
        if p.is_file()
    }

    missing = standard_filenames - student_filenames
    extra = student_filenames - standard_filenames

    per_item_deduction = (len(missing) ) * 6 / len(standard_filenames) + len(extra) * 1

    if missing:
        remarks.append(f'missing ({len(missing)}): {sorted(missing)}')
    if extra:
        remarks.append(f'extra ({len(extra)}): {sorted(extra)}')
    if per_item_deduction:
        remarks.append(f'-{per_item_deduction} ({len(missing)} missing + {len(extra)} extra)  * 6 / total_files')

    total_deduction = deduction + per_item_deduction
    score = max(0, 6 - total_deduction)
    return score, ' | '.join(remarks) if remarks else ''


def compare_to_standard(
    wd: Path,
    standard: Path,
    run_result: subprocess.CompletedProcess,
) -> tuple[float, list[str]]:
    marks   = 0.0
    remarks = []
    
    m, r = check_only_mock_grading(wd)
    marks += m
    if r:
        remarks.append(r)

    m, r = check_file_structure(wd, standard)
    marks += m
    if r:
        remarks.append(r)
    
    m, r = check_no_output(run_result)
    marks += m
    if r:
        remarks.append(r)
    
    m, r = check_named_mock_grading(wd)
    marks += m
    if r:
        remarks.append(r)

    return marks, remarks




def grade_student(student_dir: Path) -> tuple[float, str]:
    

    if not copy_script(student_dir, BASH_SCRIPT_NAME):
        return 0, 'download.sh not found in submission'

    if len(WEBSITE_TESTCASES) != len(TESTCASE_WEIGHTS):
        return 0, 'GRADER ERROR: testcase/weight count mismatch'

    total_marks   = 0.0
    total_remarks = []

    for index, (url, cut_dirs) in enumerate(WEBSITE_TESTCASES):
        weight = TESTCASE_WEIGHTS[index]
        refresh_workdir()

        if not copy_script(student_dir, BASH_SCRIPT_NAME):
            return 0, 'download.sh not found in submission'
        
        try:
            result = subprocess.run(
                ['bash', BASH_SCRIPT_NAME, url, str(cut_dirs)],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            total_remarks.append('TIMEOUT: download.sh took too long')
            total_marks += 0.0
            continue

        if index == 0:
            marks, remarks = compare_to_standard(work_dir, STANDARD_DIR_TC01, result)
        elif index == 1:
            marks, remarks = compare_to_standard(work_dir, STANDARD_DIR_TC02, result)
        elif index == 2:
            marks, remarks = compare_to_standard(work_dir, STANDARD_DIR_TC03, result)
        else:
            return 0, 'GRADER ERROR: unexpected testcase index'

        total_marks   += marks * weight
        total_remarks += remarks

    return min(total_marks, TOTAL_MARKS), ' | '.join(total_remarks)


# ── main ──────────────────────────────────────────────────────────────────────

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
from pathlib import Path
import subprocess
import shutil
import csv

SUBMISSIONS   = 'restructured_submissions'
WORK_DIR      = 'workDir'

submissions_dir = Path(SUBMISSIONS)
work_dir        = Path(WORK_DIR)


def refresh_workdir():
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir()


def copy_script(student_dir: Path, script_name: str):
    src = student_dir / script_name
    if src.exists():
        shutil.copy(src, work_dir / script_name)
        return True
    return False


def run_script(script_name: str, args: list[str] = (), cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ['bash', script_name, *args],
        cwd=cwd or work_dir,
        capture_output=True,
        text=True,
        timeout=60,
    )


def write_grades(csv_path: Path, rows: list[dict]):    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'marks', 'remarks'])
        writer.writeheader()
        writer.writerows(rows)


def append_grade(csv_path: Path, student_id: str, marks: int | float, remarks: str):
    exists = csv_path.exists()
    with open(csv_path, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'marks', 'remarks'])
        if not exists:
            writer.writeheader()
        writer.writerow({'id': student_id, 'marks': marks, 'remarks': remarks})
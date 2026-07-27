from __future__ import annotations

import subprocess
import sys

SCRIPTS = [
    "grade_download.py",
    "grade_organise.py",
    "grade_evaluate.py",
]


def main() -> int:
    for script in SCRIPTS:
        print(f"Running {script}...")
        result = subprocess.run([sys.executable, script])
        if result.returncode != 0:
            print(f"Stopping: {script} exited with {result.returncode}")
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

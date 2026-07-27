from pathlib import Path
import shutil

SUBMISSIONS_DIR = Path("submissions")
FINAL_DIR = Path("final_submissions")

# ============================================================
# CONFIGURATION
# ============================================================

EXPECTED_ITEMS = {
    "q1": "dir",
    "q2": "dir",
}

IGNORED_ITEMS = {
    "__MACOSX",
}

# ============================================================


def has_any_expected_item(path: Path) -> bool:
    """
    Return True if at least one expected file/directory exists.
    """

    for name, item_type in EXPECTED_ITEMS.items():
        item = path / name

        if item_type == "dir" and item.is_dir():
            return True

        if item_type == "file" and item.is_file():
            return True

    return False


def get_submission_root(submission: Path) -> Path | None:
    """
    Find the actual submission root.

    Valid examples:

        submission/
        ├── q1/
        └── q2/

        submission/
        └── q1/

        submission/
        └── wrapper/
            └── q2/
    """

    # At least one expected item exists at current level
    if has_any_expected_item(submission):
        return submission

    directories = [
        path
        for path in submission.iterdir()
        if path.is_dir() and path.name not in IGNORED_ITEMS
    ]

    # At most one unnecessary wrapper level
    if len(directories) != 1:
        return None

    candidate = directories[0]

    if has_any_expected_item(candidate):
        return candidate

    return None


def process_submission(submission: Path):
    source = get_submission_root(submission)

    if source is None:
        print(
            f"[ERROR] {submission.name}: "
            "no expected items found"
        )
        return

    destination = FINAL_DIR / submission.name

    if destination.exists():
        shutil.rmtree(destination)

    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(*IGNORED_ITEMS),
    )

    if source == submission:
        print(f"[OK]    {submission.name}")
    else:
        print(
            f"[FIXED] {submission.name}: "
            f"removed wrapper '{source.name}'"
        )


def main():
    FINAL_DIR.mkdir(exist_ok=True)

    for submission in SUBMISSIONS_DIR.iterdir():
        if not submission.is_dir():
            continue

        if submission.name in IGNORED_ITEMS:
            continue

        process_submission(submission)


if __name__ == "__main__":
    main()
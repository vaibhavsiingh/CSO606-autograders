from pathlib import Path
import csv
import shutil


unstructured_dir = Path('assignment 6/submissions')
structured_dir = Path('assignment 6/final_submissions')
report_path = Path('assignment 6/restructuring_problems.csv')

required_files = {
    # 'q1': ["q1_t1.py", "q1_t2.py", "q1_t3.py", "q1_t4.py"],
    # 'q2': ["projectile.py"],
    # 'q3': ["delivery_hub.py"]
}

SEARCH_MAIN_DIR_FOR = {'q1', 'q2', 'q3'}


QUESTION_LEVEL_FILENAMES = {
    'q1': 'q1.py',
    'q2': 'q2.py',
    'q3': 'q3.py',
    'q4': 'q4.py',
    'q5': 'q5.py',
}


def extract_eoid(name: str) -> str:
    candidate = name.split('_', 3)[3]
    return candidate.split('-')[0]


def ensure_copy(source_file: Path, destination_file: Path) -> None:
    destination_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_file, destination_file)


def find_first_matching_file(search_root: Path, file_name: str) -> Path | None:
    direct_match = search_root / file_name
    if direct_match.exists():
        return direct_match

    for candidate in search_root.rglob(file_name):
        if candidate.is_file():
            return candidate
    return None


def find_named_file(file_name: str, *roots: Path | None) -> Path | None:
    """Look for a specific file sitting directly in one of the given
    root directories, instead of inside a q-named subfolder."""
    for root in roots:
        if root is None:
            continue
        candidate = root / file_name
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def safe_relative(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def gather_files(
    search_root: Path,
    files: list[str],
    destination_root: Path,
    q_key: str | None = None,
    extra_roots: tuple[Path | None, ...] = (),
    report_base: Path | None = None,
) -> list[str]:
    issues = []
    base = report_base or search_root

    for file_name in files:
        source_file = find_first_matching_file(search_root, file_name)
        found_via = None  # None | 'main_dir' | 'question_level'

        # 1. Look for the exact required filename directly in the main
        #    submission dir / nested eoid dir (if enabled for this question).
        if source_file is None:
            for root in extra_roots:
                if root is None:
                    continue
                candidate = find_first_matching_file(root, file_name)
                if candidate is not None:
                    source_file = candidate
                    found_via = 'main_dir'
                    break

        # 2. Only for single-file questions: look for the configured
        #    question-level filename (e.g. "q2.py", "q3.txt", whatever
        #    you set in QUESTION_LEVEL_FILENAMES).
        if source_file is None and q_key is not None and len(files) == 1:
            configured_name = QUESTION_LEVEL_FILENAMES.get(q_key)
            if configured_name is not None:
                fallback_file = find_named_file(configured_name, *extra_roots)
                if fallback_file is not None:
                    source_file = fallback_file
                    found_via = 'question_level'

        if source_file is None:
            issues.append(f'missing {file_name}')
            continue

        ensure_copy(source_file, destination_root / file_name)

        if found_via == 'main_dir':
            issues.append(
                f'found {file_name} in main directory at {safe_relative(source_file, base)}'
            )
        elif found_via == 'question_level':
            issues.append(
                f'found {file_name} via question-level file {safe_relative(source_file, base)}'
            )
        elif source_file.parent != search_root:
            issues.append(f'found {file_name} at {source_file.relative_to(search_root)}')

    return issues


structured_dir.mkdir(parents=True, exist_ok=True)

rows = []

for submission in unstructured_dir.iterdir():
    if not submission.is_dir():
        continue

    eoid = extract_eoid(submission.name)
    destination_root = structured_dir / eoid
    destination_root.mkdir(parents=True, exist_ok=True)

    issues = []
    case = 'recursive_search'

    direct = {q: submission / q for q in required_files}
    nested_root = submission / eoid
    nested = {q: nested_root / q for q in required_files}

    if all(direct[q].exists() for q in required_files):
        case = 'direct_q_folders'
        for q, files in required_files.items():
            extra = (submission, nested_root) if q in SEARCH_MAIN_DIR_FOR else ()
            issues.extend(
                gather_files(
                    direct[q], files, destination_root / q,
                    q_key=q, extra_roots=extra, report_base=submission,
                )
            )

    elif all(nested[q].exists() for q in required_files):
        case = 'nested_eoid_q_folders'
        for q, files in required_files.items():
            extra = (nested_root, submission) if q in SEARCH_MAIN_DIR_FOR else ()
            issues.extend(
                gather_files(
                    nested[q], files, destination_root / q,
                    q_key=q, extra_roots=extra, report_base=submission,
                )
            )

    else:
        issues.append('used recursive search')

        for q, files in required_files.items():
            extra = (submission, nested_root) if q in SEARCH_MAIN_DIR_FOR else ()
            for file_name in files:
                source_file = find_first_matching_file(submission, file_name)
                found_via = None

                if source_file is None and len(files) == 1:
                    configured_name = QUESTION_LEVEL_FILENAMES.get(q)
                    if configured_name is not None:
                        fallback_file = find_named_file(configured_name, *extra)
                        if fallback_file is not None:
                            source_file = fallback_file
                            found_via = 'question_level'

                if source_file is None:
                    issues.append(f'missing {file_name}')
                    continue

                ensure_copy(source_file, destination_root / q / file_name)

                if found_via == 'question_level':
                    issues.append(
                        f'found {file_name} via question-level file '
                        f'{source_file.relative_to(submission)}'
                    )
                elif source_file.parent != direct[q] and source_file.parent != nested[q]:
                    issues.append(
                        f'found {file_name} at {source_file.relative_to(submission)}'
                    )

        q1_configured_name = QUESTION_LEVEL_FILENAMES.get('q1')
        if len(required_files['q1']) > 1 and q1_configured_name is not None:
            stray_q1 = find_named_file(q1_configured_name, submission, nested_root)
            if stray_q1 is not None:
                issues.append(
                    f'found {q1_configured_name} at {stray_q1.relative_to(submission)} but q1 '
                    f'needs {len(required_files["q1"])} separate files — manual review needed'
                )

    rows.append({
        'submission': submission.name,
        'eoid': eoid,
        'case': case,
        'issues': '; '.join(issues) if issues else '',
    })


with report_path.open('w', newline='', encoding='utf-8') as report_file:
    writer = csv.DictWriter(
        report_file,
        fieldnames=['submission', 'eoid', 'case', 'issues']
    )
    writer.writeheader()
    writer.writerows(rows)
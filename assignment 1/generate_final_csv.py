#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DEFAULT_REMARKS = Path("final_final_grading") / "overall" / "remarks.csv"
DEFAULT_STUDENTS = Path("..") / "PDT Students List.xlsx"


def normalize_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def load_remarks(path: Path) -> Dict[str, Tuple[int, str]]:
    remarks: Dict[str, Tuple[int, str]] = {}
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            student_id = normalize_value(row.get("student_id"))
            if not student_id:
                continue
            total_raw = row.get("total")
            try:
                total = int(total_raw) if total_raw is not None else 0
            except ValueError:
                total = 0
            remark_text = normalize_value(row.get("remarks"))
            remarks[student_id] = (total, remark_text)
    return remarks


def read_students_excel(path: Path) -> Tuple[List[str], List[List[str]]]:
    try:
        import openpyxl
    except ImportError as exc:
        raise RuntimeError(
            "openpyxl is required to read the Excel file. Install it with: pip install openpyxl"
        ) from exc

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], []

    headers = [normalize_value(value) for value in rows[0]]
    data_rows: List[List[str]] = []
    for row in rows[1:]:
        values = [normalize_value(value) for value in row]
        if any(values):
            data_rows.append(values)

    return headers, data_rows


def find_header_index(headers: List[str], name: str) -> Optional[int]:
    for idx, header in enumerate(headers):
        if header.strip().lower() == name.strip().lower():
            return idx
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge student list with marks and remarks.")
    parser.add_argument("--students", type=str, default=str(DEFAULT_STUDENTS), help="Path to Excel student list")
    parser.add_argument("--remarks", type=str, default=str(DEFAULT_REMARKS), help="Path to remarks CSV")
    parser.add_argument("--output", type=str, help="Output CSV path")
    parser.add_argument("--eo-col", type=str, default="EO ID", help="Column header for EO ID")
    parser.add_argument("--first-cols", type=int, default=3, help="Number of leading columns to include")
    parser.add_argument("--missing-remark", type=str, default="No submission", help="Remark for missing submissions")
    args = parser.parse_args()

    students_path = Path(args.students)
    remarks_path = Path(args.remarks)

    if not students_path.exists():
        print(f"Error: student list not found: {students_path}")
        return 2
    if not remarks_path.exists():
        print(f"Error: remarks file not found: {remarks_path}")
        return 2

    headers, student_rows = read_students_excel(students_path)
    if not headers:
        print("Error: student list is empty")
        return 2

    eo_idx = find_header_index(headers, args.eo_col)
    if eo_idx is None:
        print("Error: EO ID column not found. Available headers:")
        for header in headers:
            if header:
                print(f"  - {header}")
        return 2

    keep_cols = min(args.first_cols, len(headers))
    output_headers = headers[:keep_cols] + ["total", "remarks"]

    remarks_map = load_remarks(remarks_path)
    remarks_map_lower = {key.lower(): value for key, value in remarks_map.items()}

    output_rows: List[Tuple[str, List[str]]] = []
    for row in student_rows:
        if eo_idx >= len(row):
            continue
        eo_id = normalize_value(row[eo_idx])
        if not eo_id:
            continue

        first_values = [normalize_value(row[i]) if i < len(row) else "" for i in range(keep_cols)]
        total, remark_text = remarks_map.get(eo_id, remarks_map_lower.get(eo_id.lower(), (0, args.missing_remark)))

        output_rows.append((eo_id, first_values + [str(total), remark_text]))

    output_rows.sort(key=lambda item: item[0].lower())

    output_path = Path(args.output) if args.output else remarks_path.parent / "final.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(output_headers)
        writer.writerows(row for _, row in output_rows)

    print(f"Wrote {len(output_rows)} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

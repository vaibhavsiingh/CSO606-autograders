from pathlib import Path
import zipfile

directory = Path("./submissions")

if not directory.exists():
    raise FileNotFoundError(f"Submissions directory not found: {directory.resolve()}")

for zip_path in directory.rglob("*.zip"):
    extract_dir =  Path("./unzipped") / str(zip_path.stem)

    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

    print(f"Extracted: {zip_path} -> {extract_dir}")
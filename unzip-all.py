from pathlib import Path
import zipfile

ZIPPED_DIRECTORY = "assignment 7/submissions-zipped"
UNZIPPED_DIRECTORY = "assignment 7/submissions"

zipped_directory = Path(ZIPPED_DIRECTORY)
unzipped_dir = Path(UNZIPPED_DIRECTORY)

for file in zipped_directory.iterdir():    
    extract_to = unzipped_dir / file.stem
    with zipfile.ZipFile(file.resolve(), 'r') as zip_ref:
        zip_ref.extractall(extract_to)    
    

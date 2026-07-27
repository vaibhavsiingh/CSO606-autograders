from pathlib import Path
import pandas as pd
import os

dir = Path("perf_submissions")
add = []

for student_dir in dir.iterdir():
    count = len(list(student_dir.iterdir()))

    if count < 1:
        add.append([student_dir.name, 0, "perf.txt not found in submission"])
        continue

    if count > 1:
        print(f"{student_dir.name} has multiple items")
    
    for item in student_dir.iterdir():
        if item.name == 'perf.txt':
            if os.path.getsize(item) > 0:
                print(f"check {student_dir.name}")
            else:
                add.append([student_dir.name, 0, "perf.txt is empty"])
        else:
            print(f"{student_dir.name} has some other file")


df = pd.DataFrame(add)

df.to_csv("q4_results.csv", mode="a", index=False, header=False)

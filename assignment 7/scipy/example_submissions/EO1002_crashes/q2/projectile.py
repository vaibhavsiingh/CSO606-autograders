import sys

data = sys.stdin.read()
lines = data.strip().splitlines()
n, k = lines[0].split()
n = int(n)

# Bug: off-by-one, will IndexError on the ANGLE/SPEED line
for i in range(1, n + 2):
    t, x, y = lines[i].split()

print("HIT 12.345")

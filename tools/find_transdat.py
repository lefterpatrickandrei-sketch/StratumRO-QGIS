import os
import glob
from pathlib import Path

search_roots = [
    r"C:\Users\lefpa\Desktop",
    r"C:\Users\lefpa\Downloads",
    r"C:\Users\lefpa\Documents",
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\OSGeo4W",
    "C:\\",
]

found = []
for root in [r"C:\Users\lefpa\Desktop", r"C:\Users\lefpa\Downloads", r"C:\Users\lefpa\Documents"]:
    if os.path.exists(root):
        for p in Path(root).rglob("*transdat*"):
            found.append(str(p))
        for p in Path(root).rglob("*.gsb"):
            found.append(str(p))

for p in [r"C:\TransDATRO", r"C:\TransDAT", r"C:\ANCPI", r"C:\Program Files\TransDATRO", r"C:\Program Files (x86)\TransDATRO", r"C:\Program Files\ANCPI", r"C:\Program Files (x86)\ANCPI"]:
    if os.path.exists(p):
        found.append(p)
        for sub in Path(p).rglob("*"):
            found.append(str(sub))

print("FOUND_FILES:")
for f in set(found):
    print(f)

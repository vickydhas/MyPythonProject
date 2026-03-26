#!/usr/bin/env python3
import csv
from pathlib import Path
import sys

BASE = Path("/Users/vickydhas/Documents/Documents_Personal/Certificates")
CSV = Path(__file__).parent / "duplicates_finder.csv"

if not BASE.exists() or not BASE.is_dir():
    print(f"Error: base path {BASE} does not exist")
    sys.exit(1)

if not CSV.exists():
    print(f"Error: csv file not found: {CSV}")
    sys.exit(1)

renamed = []
skipped = []
errors = []

with CSV.open("r", encoding="utf-8", newline="") as fh:
    reader = csv.reader(fh)
    header = next(reader, None)
    for row in reader:
        if not row or len(row) < 2:
            continue
        orig, new = row[0].strip(), row[1].strip()
        if not orig or not new:
            continue
        src = BASE / orig
        dst = BASE / new
        if not src.exists():
            # try to find case-insensitive match
            matches = [p for p in BASE.iterdir() if p.name.lower() == orig.lower()]
            if matches:
                src = matches[0]
            else:
                skipped.append((orig, new, 'source not found'))
                print(f"SKIP: source not found: {orig}")
                continue
        # if destination exists, find a non-colliding name
        if dst.exists():
            base = dst.stem
            ext = dst.suffix
            i = 1
            while True:
                candidate = BASE / f"{base}_renamed_{i}{ext}"
                if not candidate.exists():
                    dst = candidate
                    break
                i += 1
        try:
            src.rename(dst)
            renamed.append((src.name, dst.name))
            print(f"RENAMED: {src.name} -> {dst.name}")
        except Exception as e:
            errors.append((src.name, dst.name, str(e)))
            print(f"ERROR renaming {src} -> {dst}: {e}")

print()
print(f"Summary: renamed={len(renamed)}, skipped={len(skipped)}, errors={len(errors)}")
if errors:
    print("Errors:")
    for e in errors:
        print(" ", e)


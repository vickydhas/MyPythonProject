# python
import hashlib
import sys
import re
import csv
from collections import defaultdict
from pathlib import Path
from typing import Optional

CHUNK_SIZE = 65536
HARD_CODED_PATH = Path("/Users/vickydhas/Documents/Documents_Personal/Certificates").expanduser()

# ------------------------ Utilities ------------------------

def sha256_of_file(p: Path):
    h = hashlib.sha256()
    try:
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
                h.update(chunk)
    except (OSError, PermissionError):
        return None
    return h.hexdigest()


def detect_extension(path: Path) -> str:
    """Detect common file extensions by magic bytes; fallback to suffix."""
    try:
        with path.open("rb") as fh:
            head = fh.read(8)
    except Exception:
        return path.suffix.lower() or ""
    if head.startswith(b"%PDF"):
        return ".pdf"
    if head[:2] == b"\xff\xd8":
        return ".jpg"
    if head.startswith(b"\x89PNG"):
        return ".png"
    if head.startswith(b"GIF8"):
        return ".gif"
    if head.startswith(b"II") or head.startswith(b"MM"):
        return ".tiff"
    return path.suffix.lower() or ""


def clean_text_for_title(s: str, max_words: int = 8, max_chars: int = 80) -> str:
    if not s:
        return ""
    t = re.sub(r"[\r\n\t]+", " ", s)
    t = re.sub(r"\s+", " ", t).strip()
    # remove trailing connectors
    t = re.sub(r"[\-:;,\.|]+$", "", t)
    t = re.sub(r"\b(and|or|&|for|with|to|of|in|on)\b[\s\-:]*$", "", t, flags=re.IGNORECASE).strip()
    words = t.split()
    if len(words) > max_words:
        t = " ".join(words[:max_words]).strip()
        t = re.sub(r"\b(and|or|&|for|with|to|of|in|on)\b$", "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"\b(a|an|the|and|or|for|with|to|of|in|on)\b$", "", t, flags=re.IGNORECASE).strip()
    # remove trailing parenthesized numbers like (1)
    t = re.sub(r"\s*\(\s*\d+\s*\)", "", t).strip()
    return t[:max_chars].strip()


def classify_text(text: str) -> str:
    t = (text or "").lower()
    if "linkedin" in t or "linkedin.com" in t:
        return "Linkedin"
    for kw in ("university", "college", "bachelor", "master", "phd", "degree", "diploma"):
        if kw in t:
            return "Academic"
    for kw in ("certificate of completion", "completed", "course", "coursera", "edx", "udemy", "training", "certification", "certificate"):
        if kw in t:
            return "Professional"
    return "Other"

# ------------------------ Core features ------------------------

def find_duplicates(root: Path):
    root = root.expanduser()
    size_map = defaultdict(list)
    for p in root.rglob("*"):
        if p.is_file():
            try:
                size_map[p.stat().st_size].append(p)
            except (OSError, PermissionError):
                continue

    dups = []
    for size, files in size_map.items():
        if len(files) < 2:
            continue
        hash_map = defaultdict(list)
        for f in files:
            h = sha256_of_file(f)
            if not h:
                continue
            hash_map[h].append(f)
        for hsum, group in hash_map.items():
            if len(group) > 1:
                dups.append({"size": size, "hash": hsum, "files": group})

    if not dups:
        print("No duplicate files found.")
        return dups

    for i, g in enumerate(dups, start=1):
        print(f"Duplicate group {i}: size={g['size']} bytes, checksum={g['hash']}")
        for p in g["files"]:
            print(f"  {p}")
        print()
    return dups


def suggest_titles(root: Path, csv_out: Optional[Path] = None):
    root = root.expanduser()
    files = sorted([p for p in root.rglob("*") if p.is_file()], key=lambda p: str(p).lower())
    if not files:
        print("No files found to suggest titles for.")
        return

    # lazy import PdfReader to avoid failing if PyPDF2 missing until needed
    try:
        from PyPDF2 import PdfReader
    except Exception:
        PdfReader = None

    results = []
    for p in files:
        det_ext = detect_extension(p)
        tag = "Other"
        suggested = None
        combined_text = ""

        if det_ext == ".pdf" and PdfReader is not None:
            try:
                reader = PdfReader(str(p))
                meta = getattr(reader, "metadata", None)
                if meta and getattr(meta, "title", None):
                    combined_text += meta.title + "\n"
                    suggested = clean_text_for_title(meta.title)
                # extract first page text
                if getattr(reader, "pages", None):
                    try:
                        first = reader.pages[0]
                        page_text = first.extract_text() or ""
                        combined_text += page_text
                        if not suggested:
                            # choose first non-empty line
                            lines = [l.strip() for l in page_text.splitlines() if l.strip()]
                            if lines:
                                suggested = clean_text_for_title(lines[0])
                    except Exception:
                        pass
            except Exception:
                suggested = None

            if not suggested:
                suggested = clean_text_for_title(re.sub(r"[_\-]+", " ", p.stem))

        else:
            # non-pdf: use cleaned stem as title and tag Other
            suggested = clean_text_for_title(re.sub(r"[_\-]+", " ", p.stem))
            combined_text = p.stem
            # ensure extension is correct
            det_ext = det_ext or p.suffix.lower()
            final = f"Other - {suggested}{det_ext}"
            print(final)
            results.append((p.name, final))
            continue

        # gather extra text (first few pages) to aid classification and course extraction
        extra_text = ""
        if det_ext == ".pdf" and PdfReader is not None:
            try:
                # reuse reader if available
                if 'reader' in locals():
                    pages = min(3, len(reader.pages))
                    for i in range(pages):
                        try:
                            extra_text += (reader.pages[i].extract_text() or "") + "\n"
                        except Exception:
                            continue
            except Exception:
                extra_text = ""

        tag = classify_text(combined_text + "\n" + extra_text + "\n" + p.stem)

        # LinkedIn filename heuristic
        stem_low = p.stem.lower()
        if re.search(r"certificate[_\-\s]*of[_\-\s]*completion", stem_low) or "certificateofcompletion" in stem_low:
            tag = "Linkedin"
            # prefer filename-derived title for LinkedIn
            fname_title = re.sub(r"(?i)certificate[_\-\s]*of[_\-\s]*completion[_\-\s]*", "", p.stem)
            fname_title = clean_text_for_title(re.sub(r"[_\-]+", " ", fname_title), max_words=12)
            if fname_title:
                suggested = fname_title

        # If suggestion still generic, try extraction heuristics
        if suggested and re.search(r"\bcertificate\b", suggested, flags=re.IGNORECASE):
            # look for course name in extra_text
            candidate = None
            m = re.search(r"(?:completed|course|program)[:\-\s]*\n?\s*(.+)", extra_text, flags=re.IGNORECASE)
            if m:
                candidate = m.group(1).splitlines()[0].strip()
            if candidate:
                suggested = clean_text_for_title(candidate)
            else:
                # fallback to filename
                suggested = clean_text_for_title(re.sub(r"[_\-]+", " ", p.stem))

        suggested = clean_text_for_title(suggested or p.stem)
        # build final title and append detected extension
        final = f"{tag} - {suggested}{det_ext or p.suffix.lower()}"
        print(final)
        results.append((p.name, final))

    # write CSV
    csv_path = csv_out or Path(__file__).with_suffix('.csv')
    try:
        with csv_path.open('w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(["Original File", "New File"])
            for row in results:
                # ensure row is (path, title)
                if isinstance(row, (list, tuple)) and len(row) >= 2:
                    w.writerow([row[0], row[1]])
                else:
                    w.writerow(["", str(row)])
        print(f"\nTitles saved to: {csv_path}")
    except Exception as e:
        print(f"Could not save CSV: {e}")


def rename_from_csv(csv_path: Optional[Path] = None, base_dir: Path = HARD_CODED_PATH, dry_run: bool = False):
    """Read CSV (Original File, New File) and rename files under base_dir.

    - csv_path: Path to CSV. If None, defaults to script sibling CSV.
    - base_dir: directory where original files live.
    - dry_run: if True, only print planned renames.
    """
    csv_path = Path(csv_path) if csv_path else Path(__file__).with_suffix('.csv')
    if not csv_path.exists():
        print(f"Rename CSV not found: {csv_path}")
        return

    renamed = []
    skipped = []
    errors = []

    with csv_path.open('r', encoding='utf-8', newline='') as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        for row in reader:
            if not row or len(row) < 2:
                continue
            orig_name = row[0].strip()
            new_name = row[1].strip()
            if not orig_name or not new_name:
                continue

            src = base_dir / orig_name
            # try case-insensitive fallback
            if not src.exists():
                matches = [p for p in base_dir.iterdir() if p.name.lower() == orig_name.lower()]
                if matches:
                    src = matches[0]
            if not src.exists():
                skipped.append((orig_name, new_name, 'source not found'))
                print(f"SKIP: source not found: {orig_name}")
                continue

            dst = base_dir / new_name
            # if destination exists, find a non-colliding name
            if dst.exists():
                base = dst.stem
                ext = dst.suffix
                i = 1
                while True:
                    candidate = base_dir / f"{base}_renamed_{i}{ext}"
                    if not candidate.exists():
                        dst = candidate
                        break
                    i += 1

            print(f"RENAME: {src.name} -> {dst.name}")
            if dry_run:
                renamed.append((src.name, dst.name))
                continue

            try:
                src.rename(dst)
                renamed.append((src.name, dst.name))
            except Exception as e:
                errors.append((src.name, dst.name, str(e)))
                print(f"ERROR renaming {src} -> {dst}: {e}")

    print(f"\nRename summary: renamed={len(renamed)}, skipped={len(skipped)}, errors={len(errors)}")
    if errors:
        print("Errors:")
        for e in errors:
            print(" ", e)


# ------------------------ CLI / entry point ------------------------

if __name__ == '__main__':
    if not HARD_CODED_PATH.exists() or not HARD_CODED_PATH.is_dir():
        print(f"Error: path {HARD_CODED_PATH} is not a directory", file=sys.stderr)
        sys.exit(1)
    find_duplicates(HARD_CODED_PATH)
    print()
    suggest_titles(HARD_CODED_PATH)
    # After generating suggestions, perform renames based on CSV (dry_run=False performs actual renames)
    rename_from_csv()

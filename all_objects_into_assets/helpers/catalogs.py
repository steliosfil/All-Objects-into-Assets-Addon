from pathlib import Path
import uuid

HEADER = [
    "# Blender Asset Catalog Definition File",
    "# UUID:catalog/path:Simple Name",
    "VERSION 1",
]

def read_cdf(cdf_path: Path):
    entries = {}
    if not cdf_path.exists():
        return entries
    with cdf_path.open("r", encoding="utf-8") as f:
        for raw in f:
            ln = raw.strip()
            if not ln or ln.startswith("#") or ln.startswith("VERSION"):
                continue
            parts = ln.split(":", 2)
            if len(parts) == 3:
                uid, path, simple = parts
                entries[path] = (uid, simple)
    return entries

def write_cdf(cdf_path: Path, entries: dict):
    if cdf_path.exists():
        try:
            backup = cdf_path.with_suffix(cdf_path.suffix + "~")
            cdf_path.replace(backup)
        except Exception:
            pass
    lines = HEADER[:]
    for cat_path in sorted(entries.keys()):
        uid, simple = entries[cat_path]
        lines.append(f"{uid}:{cat_path}:{simple}")
    cdf_path.write_text("\n".join(lines), encoding="utf-8")

def ensure_catalog(entries: dict, cat_path: str, simple_name: str) -> str:
    """Return catalog UUID; create if missing."""
    if cat_path in entries:
        return entries[cat_path][0]
    uid = str(uuid.uuid4())
    entries[cat_path] = (uid, simple_name)
    return uid

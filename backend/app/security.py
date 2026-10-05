from pathlib import Path

def resolve_static(root: Path, rel: str) -> Path | None:
    try:
        base = root.resolve()
        candidate = (base / rel).resolve()
    except (OSError, ValueError):
        return None

    if candidate.is_relative_to(base) and candidate.is_file():
        return candidate
    return None

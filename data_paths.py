"""Central path resolver for source and derived datasets in ``data/``."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"
CATALOG_PATH = DATA_ROOT / "catalog.json"


def _catalog() -> dict[str, dict[str, str]]:
    try:
        payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload.get("files", {})


def data_path(name: str, *, for_write: bool = False) -> Path:
    """Resolve a dataset by its public filename, creating its folder for writes."""
    if Path(name).name != name or not name.lower().endswith((".csv", ".xlsx", ".xls", ".json", ".html")):
        raise ValueError(f"Expected a dataset filename, got {name!r}")

    entry = _catalog().get(name)
    if entry:
        path = ROOT / entry["path"]
        if for_write:
            path.parent.mkdir(parents=True, exist_ok=True)
        return path

    matches = list(DATA_ROOT.rglob(name)) if DATA_ROOT.exists() else []
    if len(matches) == 1:
        if for_write:
            matches[0].parent.mkdir(parents=True, exist_ok=True)
        return matches[0]
    if len(matches) > 1:
        raise FileExistsError(f"Dataset filename is ambiguous: {name}")

    if for_write:
        path = DATA_ROOT / "derived" / "generated" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    raise FileNotFoundError(f"Dataset not found in data/: {name}")

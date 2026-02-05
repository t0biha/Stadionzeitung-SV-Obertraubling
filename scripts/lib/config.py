from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_config() -> dict[str, Any]:
    root = project_root()
    candidates = [root / "project_config.json", root / "scripts" / "project_config.json"]
    for config_path in candidates:
        if config_path.exists():
            return json.loads(config_path.read_text(encoding="utf-8"))
    raise FileNotFoundError(
        "project_config.json nicht gefunden. Bitte im scripts-Ordner ablegen."
    )


def resolve_path(path_str: str) -> Path:
    root = project_root()
    return root / path_str

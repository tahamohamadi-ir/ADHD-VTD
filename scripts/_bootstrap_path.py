from __future__ import annotations

import sys
from pathlib import Path


def add_project_root_to_path() -> Path:
    """
    Add project root to sys.path so scripts can import src.* modules and read project-relative files.
    This makes scripts executable from either the project root or the scripts/ directory.
    """
    current = Path(__file__).resolve()

    for parent in [current.parent, *current.parents]:
        if (parent / "src").exists() and (parent / "data").exists():
            if str(parent) not in sys.path:
                sys.path.insert(0, str(parent))
            return parent

    raise RuntimeError("Could not find project root containing src/ and data/")


PROJECT_ROOT = add_project_root_to_path()

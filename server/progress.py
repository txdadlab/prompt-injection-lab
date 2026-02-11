"""JSON-file based progress persistence for single-user local app."""

import json
import os
from typing import Any

import config
from levels.definitions import LEVELS


def _default_progress() -> dict[str, Any]:
    """Create default progress structure with all levels."""
    return {
        str(level_id): {"solved": False, "attempts": 0}
        for level_id in LEVELS
    }


def _ensure_data_dir():
    os.makedirs(config.DATA_DIR, exist_ok=True)


def load() -> dict[str, Any]:
    """Load progress from JSON file, creating default if missing."""
    _ensure_data_dir()
    if not os.path.exists(config.PROGRESS_FILE):
        return _default_progress()
    try:
        with open(config.PROGRESS_FILE, "r") as f:
            data = json.load(f)
        # Ensure all levels exist in progress
        default = _default_progress()
        for level_id in default:
            if level_id not in data:
                data[level_id] = default[level_id]
        return data
    except (json.JSONDecodeError, IOError):
        return _default_progress()


def save(progress: dict[str, Any]):
    """Save progress to JSON file."""
    _ensure_data_dir()
    with open(config.PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def record_attempt(level_id: int, solved: bool = False):
    """Record an attempt for a level, optionally marking it solved."""
    progress = load()
    key = str(level_id)
    progress[key]["attempts"] += 1
    if solved:
        progress[key]["solved"] = True
    save(progress)


def reset_level(level_id: int):
    """Reset progress for a specific level."""
    progress = load()
    progress[str(level_id)] = {"solved": False, "attempts": 0}
    save(progress)


def reset_all():
    """Reset all progress."""
    save(_default_progress())

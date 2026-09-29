"""
Shared config loader for OpenClaw snapshot scripts.
Reads .env file from the skill's root directory (one level up from scripts/).
"""

import sys
from pathlib import Path

# Skill root is the parent of the scripts/ directory
SKILL_DIR = Path(__file__).parent.parent
ENV_FILE = SKILL_DIR / ".env"

# What to snapshot when SNAPSHOT_FOLDERS is not set (backwards compatible).
DEFAULT_SNAPSHOT_FOLDERS = [".openclaw"]


def get_snapshot_folders(config: dict) -> list[str]:
    """
    Parse SNAPSHOT_FOLDERS into a clean list of paths, each interpreted
    relative to the user's home directory.

    SNAPSHOT_FOLDERS is a comma-separated list, e.g.:
        SNAPSHOT_FOLDERS=.openclaw, projects, notes

    Each entry may be a direct child of home (.openclaw) or a nested path
    (projects/myapp). Leading/trailing slashes are stripped. If the value is
    unset or empty, falls back to [".openclaw"] so existing setups keep working.
    """
    raw = (config.get("SNAPSHOT_FOLDERS") or "").strip()
    if not raw:
        return list(DEFAULT_SNAPSHOT_FOLDERS)

    folders = []
    for entry in raw.split(","):
        entry = entry.strip().strip("/")
        if entry and entry not in folders:
            folders.append(entry)
    return folders or list(DEFAULT_SNAPSHOT_FOLDERS)


def load_env() -> dict:
    """Read .env file and return as dict."""
    if not ENV_FILE.is_file():
        print(f"Error: .env file not found at {ENV_FILE}")
        print(f"Run this first:  cp .env.example .env  (then fill in your values)")
        sys.exit(1)

    config = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            config[key.strip()] = value.strip()
    return config


def get_config() -> dict:
    """Load and validate the config."""
    config = load_env()

    required = ["BACKUP_PASSWORD", "GITHUB_PAT", "GITHUB_USERNAME"]
    missing = [k for k in required if not config.get(k)]

    if missing:
        print("Error: Missing values in .env file:")
        for k in missing:
            print(f"  - {k}")
        sys.exit(1)

    config.setdefault("REPO_NAME", "openclaw-transport")
    config["REPO_URL"] = (
        f"https://{config['GITHUB_PAT']}@github.com/"
        f"{config['GITHUB_USERNAME']}/{config['REPO_NAME']}.git"
    )

    # Parsed list of folders to snapshot (relative to home). Defaults to
    # [".openclaw"] when SNAPSHOT_FOLDERS is unset.
    config["SNAPSHOT_FOLDERS_LIST"] = get_snapshot_folders(config)

    return config

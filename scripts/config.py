"""
Shared config loader for OpenClaw snapshot scripts.
Reads .env file from the skill's root directory (one level up from scripts/).
"""

import os
import shutil
import subprocess
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


def gh(args: list[str], token: str = "") -> str:
    """Run a GitHub CLI command and return its stripped stdout, or "" if gh is
    missing, not logged in, or the command fails. If token is given, gh uses it
    (via GH_TOKEN) instead of its own login."""
    if shutil.which("gh") is None:
        return ""
    env = dict(os.environ, GH_TOKEN=token) if token else None
    result = subprocess.run(["gh", *args], capture_output=True, text=True, env=env)
    return result.stdout.strip() if result.returncode == 0 else ""


def resolve_github_auth(config: dict):
    """Fill GITHUB_PAT / GITHUB_USERNAME from the GitHub CLI when blank in .env.

    Resolution order for each: .env value first, then the gh login.
    The username is looked up with whichever token is actually in use, so the
    two can never point at different accounts."""
    if config.get("GITHUB_PAT"):
        config["AUTH_SOURCE"] = ".env GITHUB_PAT"
    else:
        config["GITHUB_PAT"] = gh(["auth", "token"])
        config["AUTH_SOURCE"] = "gh login"

    if not config.get("GITHUB_USERNAME") and config.get("GITHUB_PAT"):
        config["GITHUB_USERNAME"] = gh(["api", "user", "--jq", ".login"], token=config["GITHUB_PAT"])


def get_config() -> dict:
    """Load and validate the config."""
    config = load_env()
    resolve_github_auth(config)

    required = ["BACKUP_PASSWORD", "GITHUB_PAT", "GITHUB_USERNAME"]
    missing = [k for k in required if not config.get(k)]

    if missing:
        print("Error: Missing values in .env file:")
        for k in missing:
            print(f"  - {k}")
        if "GITHUB_PAT" in missing or "GITHUB_USERNAME" in missing:
            print("  GITHUB_PAT / GITHUB_USERNAME can be left blank if the GitHub CLI")
            print("  is installed and logged in on this machine:  gh auth login")
        sys.exit(1)

    print(f"GitHub auth: {config['AUTH_SOURCE']} (user: {config['GITHUB_USERNAME']})")

    # Not setdefault: .env.example ships "REPO_NAME=" (present but empty),
    # and setdefault only fills keys that are missing entirely.
    if not config.get("REPO_NAME"):
        config["REPO_NAME"] = "xo-workspace-backup"
    config["REPO_URL"] = (
        f"https://{config['GITHUB_PAT']}@github.com/"
        f"{config['GITHUB_USERNAME']}/{config['REPO_NAME']}.git"
    )

    # Parsed list of folders to snapshot (relative to home). Defaults to
    # [".openclaw"] when SNAPSHOT_FOLDERS is unset.
    config["SNAPSHOT_FOLDERS_LIST"] = get_snapshot_folders(config)

    return config

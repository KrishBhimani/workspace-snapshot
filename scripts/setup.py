#!/usr/bin/env python3
"""
OpenClaw Snapshot — One-Time Setup
Installs GPG and sets up the GitHub transport repo.
Safe to run multiple times.
"""

import os
import shutil
import sys
import subprocess
from config import get_config, gh, SKILL_DIR, LEGACY_LOCAL_REPO


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    kwargs.setdefault("check", True)
    kwargs.setdefault("text", True)
    kwargs.setdefault("capture_output", True)
    return subprocess.run(cmd, **kwargs)


def install_gpg():
    result = subprocess.run(["which", "gpg"], capture_output=True)
    if result.returncode == 0:
        print("✓ GPG already installed")
        return

    print("  Installing GPG...")
    subprocess.run(
        ["sudo", "apt-get", "update", "-qq"],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["sudo", "apt-get", "install", "-y", "-qq", "gnupg", "gpg-agent"],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    print("✓ GPG installed")


def ensure_remote_repo(config: dict):
    """Create the transport repo on GitHub as private if it doesn't exist.
    No-op when gh isn't installed/authenticated — the push below then fails
    with the usual 'make sure the repo exists' message."""
    full_name = f"{config['GITHUB_USERNAME']}/{config['REPO_NAME']}"
    token = config["GITHUB_PAT"]

    if gh(["repo", "view", full_name, "--json", "name"], token=token):
        return  # exists (just empty)

    print(f"  Repo {full_name} not found — creating it (private) via gh...")
    if gh(["repo", "create", full_name, "--private"], token=token) or \
            gh(["repo", "view", full_name, "--json", "name"], token=token):
        print(f"✓ Created private repo {full_name}")
    else:
        print("  Could not create the repo via gh (not installed, not logged in,")
        print("  or token lacks permission). Create it manually on GitHub as private.")


def migrate_legacy_repo(config: dict):
    """Move an old ~/openclaw-transport working copy to ~/<REPO_NAME>, but only
    if it tracks the same GitHub repo. A copy of a different repo is left
    alone — pointing it at the new repo would push unrelated history there."""
    local_repo = config["LOCAL_REPO"]
    if local_repo == LEGACY_LOCAL_REPO or local_repo.exists():
        return
    if not (LEGACY_LOCAL_REPO / ".git").is_dir():
        return

    origin = run(
        ["git", "-C", str(LEGACY_LOCAL_REPO), "remote", "get-url", "origin"], check=False,
    ).stdout.strip()
    expected = f"github.com/{config['GITHUB_USERNAME']}/{config['REPO_NAME']}.git".lower()

    if origin.lower().endswith(expected):
        shutil.move(str(LEGACY_LOCAL_REPO), str(local_repo))
        print(f"✓ Moved {LEGACY_LOCAL_REPO} → {local_repo}")
    else:
        print(f"  Note: {LEGACY_LOCAL_REPO} belongs to a different repo and is no longer used.")
        print(f"  Its backups are still on GitHub; delete the local folder when you like.")


def setup_repo(config: dict):
    repo_url = config["REPO_URL"]
    local_repo = config["LOCAL_REPO"]
    migrate_legacy_repo(config)

    if (local_repo / ".git").is_dir():
        run(["git", "-C", str(local_repo), "remote", "set-url", "origin", repo_url])
        run(["git", "-C", str(local_repo), "pull", "origin", "main", "--quiet"], check=False)
        print(f"✓ Repo already exists at {local_repo} — remote URL updated")
        return

    # Try cloning first (preserves existing backups on GitHub)
    print("  Cloning from GitHub...")
    result = run(["git", "clone", repo_url, str(local_repo)], check=False)

    if result.returncode == 0:
        print("✓ Repo cloned (existing backups preserved)")
        return

    # Clone failed — the repo may not exist yet. If gh is available, create it
    # as a private repo (never public: manifests are plain text).
    ensure_remote_repo(config)

    # Repo is empty/new, so init fresh
    print("  Repo appears empty, initializing...")
    local_repo.mkdir(parents=True, exist_ok=True)
    os.chdir(local_repo)

    run(["git", "init"])
    run(["git", "remote", "add", "origin", repo_url])
    run(["git", "commit", "--allow-empty", "-m", "init"])
    run(["git", "branch", "-M", "main"])

    result = run(["git", "push", "-u", "origin", "main"], check=False)
    if result.returncode != 0:
        print(f"✗ Push failed: {result.stderr.strip()}")
        print("  Check your GITHUB_USERNAME, GITHUB_PAT, and make sure the repo exists on GitHub.")
        sys.exit(1)

    print("✓ Repo initialized and pushed")


def main():
    print("=" * 50)
    print("  OpenClaw Snapshot — Setup")
    print("=" * 50)
    print()

    config = get_config()
    print("✓ Config loaded from .env")
    print(f"  GitHub user: {config['GITHUB_USERNAME']}")
    print(f"  Repo: {config['REPO_NAME']}")
    print()

    print("[1/2] Checking GPG...")
    install_gpg()
    print()

    print("[2/2] Setting up GitHub transport repo...")
    setup_repo(config)
    print()

    print("=" * 50)
    print("  Setup complete!")
    print("=" * 50)
    print()
    print(f"  To backup:   python3 {SKILL_DIR}/scripts/backup.py")
    print(f"  To restore:  python3 {SKILL_DIR}/scripts/restore.py")
    print()


if __name__ == "__main__":
    main()
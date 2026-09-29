---
name: snapshot
description: >
  Backup and restore the .openclaw agent folder — encrypted snapshots pushed to a
  private GitHub repo. Use this skill whenever the user mentions backup, restore,
  snapshot, save state, migrate workspace, move to a new machine, or any request
  to preserve or recover the .openclaw agent. Also trigger when the user asks
  about available backup versions, wants to check backup status, or needs to set
  up the backup system on a new workspace. Even casual phrasing like "save my
  agent" or "load my stuff on the new box" should trigger this skill.
---

# Snapshot — OpenClaw Backup & Restore

Encrypted backup and restore for the `~/.openclaw` agent folder (and any other
home-relative folders you configure).  
Backups are GPG-encrypted, chunked for GitHub's 100MB file limit, and pushed to a private repo.

## How it works

- **backup** — tar.gz → GPG encrypt → split into ≤95MB chunks → push to GitHub
- **restore** — clone repo → pick version → reassemble chunks → verify checksum → decrypt → extract
- **setup** — install GPG, clone/init the GitHub transport repo

By default only `~/.openclaw` is backed up. Set `SNAPSHOT_FOLDERS` in `.env` to back
up additional folders (see Prerequisites below).

Each backup version lives in its own folder with a manifest. The folder is named
`openclaw-{timestamp}` by default, or a custom name if you pass `--name`:
```
backups/openclaw-{timestamp}/      (or backups/{custom-name}/)
├── manifest.json
├── part-000.gpg
├── part-001.gpg
└── ...
```

Last 10 backups are kept (by timestamp); older ones are auto-deleted.

---

## Prerequisites

Before running any command, verify:

1. **GPG is installed.** If not: `sudo apt-get update && sudo apt-get install -y gnupg gpg-agent`
2. **The `.env` file exists** in this skill's directory with valid values. If not, copy from `.env.example` and fill in: `cp .env.example .env`
3. **Setup has been run at least once** on this workspace: `python3 scripts/setup.py`

The `.env` file must contain:
```
BACKUP_PASSWORD=<strong passphrase>
GITHUB_PAT=<GitHub personal access token with repo scope>
GITHUB_USERNAME=<GitHub username>
REPO_NAME=openclaw-transport
```

Optional — back up more than just `.openclaw`. `SNAPSHOT_FOLDERS` is a
comma-separated list of folders relative to home (e.g. `/home/coder`). Entries
may be direct children of home or nested paths. Defaults to `.openclaw`:
```
SNAPSHOT_FOLDERS=.openclaw, projects, notes
```

---

## Commands

All scripts live in the `scripts/` subdirectory of this skill.

### Take a backup
```bash
python3 <skill-path>/scripts/backup.py

# Give the backup folder a custom name in GitHub (instead of openclaw-<timestamp>)
python3 <skill-path>/scripts/backup.py --name stable-config
```
Non-interactive. Compresses, encrypts, chunks if needed, pushes to GitHub.  
Backs up the folders listed in `SNAPSHOT_FOLDERS` (default `.openclaw`).  
Auto-deletes versions older than the most recent 10.

### Restore a backup
```bash
# Restore the latest version (non-interactive, best for AI agents)
python3 <skill-path>/scripts/restore.py --latest

# Restore a specific backup by its name (or timestamp)
python3 <skill-path>/scripts/restore.py --name stable-config
python3 <skill-path>/scripts/restore.py --name openclaw-20260227-120000

# List available versions without restoring
python3 <skill-path>/scripts/restore.py --list

# Interactive mode (prompts user to pick — use only in human-attended sessions)
python3 <skill-path>/scripts/restore.py
```

### Run setup (first time or new workspace)
```bash
python3 <skill-path>/scripts/setup.py
```
Safe to run multiple times. Installs GPG if missing, clones or syncs the transport repo.

---

## Typical workflows

**Always run setup.py before backup or restore.** It's idempotent (safe to run every time) and ensures GPG is installed, the transport repo exists, and the local repo is synced with GitHub. This prevents issues like missing repos, stale local state, or remotely deleted backups not being reflected locally.

### "Back up my agent"
1. Run `python3 <skill-path>/scripts/setup.py`
2. Run `python3 <skill-path>/scripts/backup.py`
3. Report the timestamp and size to the user

### "Restore my agent" or "Load the latest backup"
1. Run `python3 <skill-path>/scripts/setup.py`
2. Run `python3 <skill-path>/scripts/restore.py --latest`
3. Tell the user it's done and suggest restarting the gateway

### "Show me available backups"
1. Run `python3 <skill-path>/scripts/setup.py`
2. Run `python3 <skill-path>/scripts/restore.py --list`
3. Present the version list to the user

### "Set up backups on this new workspace"
1. Confirm the user has a `.env` file with credentials (help them create one from `.env.example` if not)
2. Run `python3 <skill-path>/scripts/setup.py`

### "Restore a specific version"
1. Run `python3 <skill-path>/scripts/setup.py`
2. Run `python3 <skill-path>/scripts/restore.py --list` to show available versions
3. Ask the user which backup they want (by name or timestamp)
4. Run `python3 <skill-path>/scripts/restore.py --name <name>`

---

## Important notes

- The `.env` file in this skill directory is **excluded from backups** (contains secrets).
- The transport repo (`~/openclaw-transport/`) lives outside the backed-up folders and is not backed up.
- By default `.openclaw` is the only folder backed up; add more via `SNAPSHOT_FOLDERS`.
- New backups are archived rooted at `$HOME` and restore each folder back to its
  original place under home. Older `.openclaw`-only backups still restore into `~/.openclaw`.
- WhatsApp sessions are excluded (workspace-specific). User must reconnect after restore.
- After restoring, the user should restart their gateway to ensure all services pick up the restored state.

---
name: snapshot
description: >
  Backup and restore the .openclaw agent folder — encrypted snapshots pushed to a
  private GitHub repo. Use this skill whenever the user wants to back up, restore,
  snapshot, save the state of, or migrate their OpenClaw agent or workspace
  (including moving it to a new machine). Also trigger when the user asks about
  available agent backup versions, wants to check backup status, or needs to set
  up the backup system on a new workspace. Even casual phrasing like "save my
  agent" or "load my stuff on the new box" should trigger this skill. Do not use
  it for unrelated backups (databases, other apps).
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

Last 10 backups are kept (by timestamp); older ones are auto-deleted from the
repo's current files. They remain in the transport repo's **git history**, so the
repo keeps growing over time — expect to prune or recreate it eventually.

---

## Prerequisites

Before running any command, verify:

1. **GPG is installed.** If not (Debian/Ubuntu): `sudo apt-get update && sudo apt-get install -y gnupg gpg-agent`
2. **A private GitHub repo exists** named `$REPO_NAME` (default `openclaw-transport`).
   If the GitHub CLI (`gh`) is installed and logged in, `setup.py` creates it
   automatically as private. Otherwise the user must create it on GitHub first
   (empty is fine). It must be **private**: chunks are encrypted, but
   `manifest.json` (backup names, folder list, sizes) is plain text.
3. **The `.env` file exists** in this skill's directory with valid values. If not, copy from `.env.example` and fill in: `cp .env.example .env`
4. **Setup has been run at least once** on this workspace: `python3 scripts/setup.py`

The `.env` file must contain:
```
BACKUP_PASSWORD=<strong passphrase>
GITHUB_PAT=<GitHub personal access token with repo scope>
GITHUB_USERNAME=<GitHub username>
```
Optional: `REPO_NAME=<repo name>` — defaults to `openclaw-transport` if unset or blank.

**Using the GitHub CLI instead of a PAT:** if `gh` is installed and logged in
*on the machine running the scripts* (`gh auth status` to check), `GITHUB_PAT`
and `GITHUB_USERNAME` can be left blank. The scripts use the gh login's token
and look up the username from it. A PAT set in `.env` always takes priority.
Each script prints which source it used (`GitHub auth: gh login (user: ...)`) —
check that it's the account the user expects. The gh login needs the `repo`
scope (a default `gh auth login` has it).

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
**Reusing a `--name` that already exists replaces that backup** — check
`restore.py --list` first and confirm with the user before overwriting a named backup.

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
**Restore is destructive.** It extracts directly into the home directory and
overwrites any existing files at the same paths, with no undo. Always confirm with
the user before restoring, and offer to take a backup of the current state first.
`--list` is read-only and safe to run anytime.

### Run setup (first time or new workspace)
```bash
python3 <skill-path>/scripts/setup.py
```
Safe to run multiple times. Installs GPG if missing, clones or syncs the transport repo,
and (if `gh` is available) creates the GitHub repo as private when it doesn't exist.

---

## Typical workflows

**Run setup.py before each backup or restore.** It's idempotent (safe to run every time). Backup depends on it: setup ensures the local transport repo (`~/openclaw-transport/`) exists and is synced with GitHub, which prevents stale local state or remotely deleted backups not being reflected. Restore doesn't use the local transport repo (it makes its own temporary clone), but setup still installs GPG and validates credentials, so run it anyway.

### "Back up my agent"
1. Run `python3 <skill-path>/scripts/setup.py`
2. Run `python3 <skill-path>/scripts/backup.py`
3. Report the timestamp and size to the user

### "Restore my agent" or "Load the latest backup"
1. Run `python3 <skill-path>/scripts/setup.py`
2. Run `python3 <skill-path>/scripts/restore.py --list` and tell the user which backup is latest
3. Warn that restoring overwrites existing files under home, and get the user's confirmation (offer a backup of the current state first)
4. Run `python3 <skill-path>/scripts/restore.py --latest`
5. Tell the user it's done and suggest restarting the gateway

### "Show me available backups"
1. Run `python3 <skill-path>/scripts/setup.py`
2. Run `python3 <skill-path>/scripts/restore.py --list`
3. Present the version list to the user

### "Set up backups on this new workspace"
1. Confirm the user has a `.env` file with `BACKUP_PASSWORD` set (help them create one from `.env.example` if not). For GitHub access, either fill in `GITHUB_PAT`/`GITHUB_USERNAME` or check `gh auth status` shows a logged-in account
2. Run `python3 <skill-path>/scripts/setup.py`

### "Restore a specific version"
1. Run `python3 <skill-path>/scripts/setup.py`
2. Run `python3 <skill-path>/scripts/restore.py --list` to show available versions
3. Ask the user which backup they want (by name or timestamp), and confirm they're OK with existing files under home being overwritten
4. Run `python3 <skill-path>/scripts/restore.py --name <name>`

---

## Important notes

- Some things are **never included in backups**, at any depth inside the snapshot folders:
  - `.env` and `.env.*` files (including this skill's `.env`, which holds secrets)
  - `.git` directories (so project git history is **not** backed up)
  - `node_modules`, `*.sock`, and `backups-repo`
  - WhatsApp sessions/credentials (see below)

  This matters most when `SNAPSHOT_FOLDERS` includes project folders. After a
  restore, those projects will have no git history or `.env` files. Tell the user
  about this when they add non-`.openclaw` folders.
- The transport repo (`~/openclaw-transport/`) lives outside the backed-up folders and is not backed up.
- By default `.openclaw` is the only folder backed up; add more via `SNAPSHOT_FOLDERS`.
- New backups are archived rooted at `$HOME` and restore each folder back to its
  original place under home. Older `.openclaw`-only backups still restore into `~/.openclaw`.
- WhatsApp sessions are excluded (workspace-specific). User must reconnect after restore.
- After restoring, the user should restart their gateway to ensure all services pick up the restored state.

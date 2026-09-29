# Workspace Snapshot: Backup & Restore Guide

Complete guide to backing up and restoring your workspace. You don't need advanced technical knowledge. Just follow the steps in order.

---

## What Do These Scripts Do?

- **backup.py** takes a snapshot of your workspace (the `.claude` folder by default, or the folders you list in `SNAPSHOT_FOLDERS`), compresses it, encrypts it with a password, and uploads it to a private GitHub repository. Large backups are automatically split into 95 MB chunks for GitHub compatibility. Each backup is saved in its own folder, named `workspace-<timestamp>` by default or a custom name if you pass `--name`, and the 10 most recent backups are kept automatically.

- **restore.py** downloads your backups from GitHub and lets you pick which version you want (or use command-line flags for automation). It reassembles chunks if needed, verifies the backup's integrity, decrypts it, and restores your folders to their original locations.

- **setup.py** installs the GPG encryption tools and connects to your GitHub repo. It's safe to run multiple times: it syncs the latest backups from GitHub without deleting anything.

Think of it like saving and loading a game: **backup** saves your progress, **restore** loads it on any machine.

---

## Folder Structure

Everything lives in one folder:

```
workspace-snapshot/
├── .env.example        ← template (shows what keys you need)
├── .env                ← your actual keys (you create this)
├── scripts/
│   ├── config.py       ← shared config loader (don't edit)
│   ├── setup.py        ← run to set things up / sync backups
│   ├── backup.py       ← run to take a backup
│   └── restore.py      ← run to restore a version
├── SKILL.md            ← instructions for AI agents
└── INSTRUCTIONS.md     ← this file
```

All your keys (password, GitHub token) live in the `.env` file, in one place that's easy to manage.

---

## Before You Start (One-Time Setup)

### Step 1: Install GPG (encryption tool)

Run this in your terminal:

```bash
sudo apt-get update && sudo apt-get install -y gnupg gpg-agent
```

This installs the tool that encrypts and decrypts your backups. You need to run this on **every new workspace** before using backup or restore. (`setup.py` also installs it if it's missing.)

### Step 2: Create a GitHub repo

**Skip this step if the GitHub CLI (`gh`) is installed and logged in.** `setup.py` will create the repo for you as private.

Otherwise:
1. Go to [github.com/new](https://github.com/new)
2. Name it `xo-workspace-backup`
3. Set it to **Private**
4. Click **Create repository**

### Step 3: Get GitHub access

**Option A: GitHub CLI (easiest).** If `gh auth status` shows you're logged in, you can leave `GITHUB_PAT` and `GITHUB_USERNAME` blank in `.env`. The scripts use your gh login.

**Option B: Personal access token.**
1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Click **"Generate new token (classic)"**
3. Give it a name like `workspace-backup`
4. Select the **`repo`** scope (full control of private repositories)
5. Click **Generate token**
6. **Copy the token immediately.** GitHub only shows it once.

(A fine-grained token also works if it has **Contents: Read and write** access to your backup repo.)

### Step 4: Fill in your .env file

Go to the workspace-snapshot folder:

```bash
cd /path/to/workspace-snapshot
cp .env.example .env
```

Now open `.env` in any editor and fill in your values:

```
BACKUP_PASSWORD=your-strong-password-here
GITHUB_PAT=ghp_xxxxxxxxxxxxxxxxxxxx
GITHUB_USERNAME=YourGitHubUsername
REPO_NAME=xo-workspace-backup
```

(`GITHUB_PAT` and `GITHUB_USERNAME` can stay blank if you're using the GitHub CLI. `REPO_NAME` defaults to `xo-workspace-backup` if left blank.)

**Optional: choose which folders to back up.** Add a `SNAPSHOT_FOLDERS` line
with a comma-separated list of folders relative to your home directory (e.g.
`/home/coder`). Leave it out to back up only `.claude`:

```
SNAPSHOT_FOLDERS=.claude, projects, notes
```

Each entry can be a direct child of home or a nested path like `work/configs`.

**Choose a strong backup password and remember it.** You'll need it if you ever restore on a machine that doesn't have this `.env` file.

### Step 5: Run setup

```bash
python3 /path/to/workspace-snapshot/scripts/setup.py
```

You'll see:

```
==================================================
  Workspace Snapshot — Setup
==================================================

GitHub auth: gh login (user: YourUsername)
✓ Config loaded from .env
  GitHub user: YourUsername
  Repo: xo-workspace-backup

[1/2] Checking GPG...
✓ GPG already installed

[2/2] Setting up GitHub transport repo...
✓ Repo cloned (existing backups preserved)

==================================================
  Setup complete!
==================================================

  To backup:   python3 /path/to/workspace-snapshot/scripts/backup.py
  To restore:  python3 /path/to/workspace-snapshot/scripts/restore.py
```

Done. You're ready to back up and restore.

---

## How to Take a Backup

```bash
python3 /path/to/workspace-snapshot/scripts/backup.py
```

To give the backup folder a custom name in GitHub (instead of the default
`workspace-<timestamp>`), add `--name`:

```bash
python3 /path/to/workspace-snapshot/scripts/backup.py --name stable-config
```

The name may use letters, digits, `.`, `-` and `_` (no spaces or slashes). If you
reuse a name, the new backup replaces the old folder of that name.

To describe what the backup is for, add `--message` (or `-m`). It becomes the git
commit message and is shown next to the backup in `restore.py --list`:

```bash
python3 /path/to/workspace-snapshot/scripts/backup.py --name stable-config --message "Working config after MCP setup"
```

The name and message are stored unencrypted, so don't put secrets in them.

**What happens:**

1. It syncs the latest from GitHub (so existing backups from other workspaces are preserved)
2. The folders in `SNAPSHOT_FOLDERS` (default just `.claude`) get compressed and encrypted
3. If the backup is larger than 95 MB, it's automatically split into chunks (see "Understanding Backup Chunks" below)
4. A `manifest.json` file is created with metadata (name, message, timestamp, folders, size, checksum, chunk info)
5. Everything gets pushed to your private GitHub repo

You'll see:

```
Folders to snapshot: .claude, projects
Syncing with GitHub...
Creating backup: stable-config
Backup created: stable-config (154.3 MB, 2 part(s))
Pushed to GitHub
Backup complete: stable-config
```

**Tip:** Run this before making big changes to your workspace, or at the end of each day.

**Running it from Claude Code:** Claude Code may block the backup as possible data exfiltration, because it uploads files from your home folder. That's expected. Run it yourself by typing `! python3 /path/to/workspace-snapshot/scripts/backup.py ...` in the prompt, or add an allow rule for the command in your Claude Code settings.

---

## Understanding Backup Chunks

**Why chunks?** GitHub has file size limits. If your backup is large, it's automatically split into 95 MB pieces.

**What it looks like on GitHub:**

```
xo-workspace-backup/backups/
└── workspace-20260929-120000/         ← Backup folder (or your custom --name)
    ├── manifest.json                  ← Metadata (name, message, timestamp, folders, size, checksum, etc.)
    ├── part-000.gpg                   ← Chunk 1 (95 MB)
    ├── part-001.gpg                   ← Chunk 2 (95 MB)
    └── part-002.gpg                   ← Chunk 3 (remainder)
```

For smaller backups (under 95 MB), you'll see just one chunk:

```
xo-workspace-backup/backups/
└── workspace-20260929-120000/
    ├── manifest.json
    └── part-000.gpg                   ← Single file (not split)
```

**The good news:** you don't need to think about this. When you restore, the scripts automatically reassemble chunks, verify checksums, and decrypt everything.

---

## How to Restore

**Restore overwrites files.** Anything in your home folder at the same path as a file in the backup is replaced, with no undo. If you're unsure, take a backup of the current state first.

### Basic restore (interactive mode)

```bash
python3 /path/to/workspace-snapshot/scripts/restore.py
```

You'll see a list of all saved versions:

```
Cloning backup repo...

Available versions (3):
------------------------------------------------------------
  [1] stable-config  (154.3 MB, 2 part(s)) ← latest
        message: Working config after MCP setup
        created: 20260929-120000
        folders: .claude, projects
  [2] workspace-20260928-090000  (48.1 MB, single file)
        folders: .claude
  [3] workspace-20260927-150000  (47.9 MB, single file)
        folders: .claude
------------------------------------------------------------

Select version [1] or press Enter for latest:
```

- Press **Enter** for the latest backup
- Type a number (1, 2, 3, etc.) to pick a specific version

The script will:
1. Download the backup from GitHub
2. Reassemble chunks if needed
3. Verify the checksum
4. Decrypt and extract your folders back to their original locations
5. Clean up temporary files automatically

You'll see:

```
Restoring: stable-config
  Reassembling chunks...
  Checksum verified ✓
  Decrypting and extracting...

Restored .claude, projects into /home/coder (from stable-config)
```

### Advanced restore modes

Use command-line flags for automation and scripting:

**Restore the latest backup (non-interactive):**
```bash
python3 /path/to/workspace-snapshot/scripts/restore.py --latest
```

**Restore a specific backup by its name (or timestamp):**
```bash
python3 /path/to/workspace-snapshot/scripts/restore.py --name stable-config
python3 /path/to/workspace-snapshot/scripts/restore.py --name workspace-20260928-090000
```
(`--version` still works as an alias and also matches a timestamp.)

**List all available backups and exit:**
```bash
python3 /path/to/workspace-snapshot/scripts/restore.py --list
```

---

## Setting Up on a New Workspace (Quick Checklist)

When you move to a fresh workspace, here's everything you need to do in order:

1. Copy the `workspace-snapshot` folder to the new workspace (or clone it from a safe location)
2. Create or update your `.env` file with your credentials (or log in with `gh auth login`)
3. Run setup to install GPG and sync backups from GitHub:
   ```bash
   python3 /path/to/workspace-snapshot/scripts/setup.py
   ```
4. Restore your workspace:
   ```bash
   python3 /path/to/workspace-snapshot/scripts/restore.py --latest
   ```
5. Log in to Claude Code again (the login token is never backed up), and start a new session so it picks up the restored settings.

That's it. Your workspace is restored on the new machine.

---

## Syncing Backups from Other Workspaces

If you backed up from a different workspace and your local `~/xo-workspace-backup` folder (or `~/<REPO_NAME>` if you set one) doesn't have the latest backups, just run setup again:

```bash
python3 /path/to/workspace-snapshot/scripts/setup.py
```

This is safe to run anytime. It pulls the latest backups from GitHub without deleting anything. After syncing, you can run `backup.py` or `restore.py` as normal.

---

## Automatic Backup Cleanup

The system **keeps the 10 most recent backups** and automatically removes older ones.

For example, if you have 15 backups:
- Backups 1–10 (newest) are kept
- Backups 11–15 (oldest) are deleted

This happens during `backup.py`. You'll see:

```
Removing old backup: workspace-20260920-050000
Backup created: workspace-20260929-120000 (154.3 MB, 2 part(s))
```

Deleted backups disappear from the repo's files but remain in its **git history**, so the repo keeps growing over time. If it gets too large, create a fresh repo and point `REPO_NAME` at it.

**If you want to keep more backups,** edit `MAX_VERSIONS` near the top of `backup.py`:
```python
MAX_VERSIONS = 10  # Change to a higher number like 20 or 50
```

---

## Where Are My Backups Stored?

On GitHub, your `xo-workspace-backup` repo's backup folder structure looks like this:

```
xo-workspace-backup/
└── backups/
    ├── workspace-20260927-150000/
    │   ├── manifest.json
    │   └── part-000.gpg
    ├── workspace-20260928-090000/
    │   ├── manifest.json
    │   └── part-000.gpg
    └── stable-config/
        ├── manifest.json
        ├── part-000.gpg
        └── part-001.gpg
```

**Key points:**
- Each backup is a **folder** (not a single file). Its name is `workspace-<timestamp>` by default, or whatever you passed to `--name`
- The `manifest.json` file contains metadata: backup name, message, timestamp, the folders included, checksum, chunk count, total size, etc.
- `part-*.gpg` files are the encrypted chunks (each ~95 MB, or smaller for the last chunk)
- The default timestamp in the folder name is in UTC (YYYYMMDD-HHMMSS)

**All backup contents are encrypted.** Without your `BACKUP_PASSWORD`, nobody can read them, not even someone with access to your GitHub repo. The manifest (names, messages, folder list, sizes) is **not** encrypted, which is why the repo must be private.

---

## What Gets Backed Up? What Doesn't?

**Included:**
- The folders you set in `SNAPSHOT_FOLDERS` (default: `.claude`), each backed up in full minus the exclusions below
- For `.claude`: settings, `CLAUDE.md`, skills, agents, plugins, and other configuration

**Excluded (for security and workspace-specific reasons):**
- `.env` and `.env.*` files (they contain secrets)
- `.git` folders (project git history is **not** backed up)
- `node_modules/` directories
- Unix socket files (`*.sock`)
- `.claude/.credentials.json` (your Claude Code login token)
- `.claude/projects/` (Claude Code session transcripts, which may contain secrets)

**⚠️ Important:** After restoring on a new machine, you'll need to log in to Claude Code again. If you back up project folders, they come back without their `.git` history and `.env` files, so keep those projects on GitHub separately.

---

## Quick Reference

| I want to...                             | Run this                                                                   |
|------------------------------------------|---------------------------------------------------------------------------|
| Install GPG (every new workspace)        | `sudo apt-get update && sudo apt-get install -y gnupg gpg-agent`         |
| First-time setup / sync backups          | `python3 /path/to/scripts/setup.py`                                      |
| Take a backup                            | `python3 /path/to/scripts/backup.py`                                     |
| Take a backup with a custom name         | `python3 /path/to/scripts/backup.py --name stable-config`               |
| Take a backup with name and message      | `python3 /path/to/scripts/backup.py --name stable-config -m "Why"`      |
| Restore a version (interactive)          | `python3 /path/to/scripts/restore.py`                                    |
| Restore latest (non-interactive)         | `python3 /path/to/scripts/restore.py --latest`                           |
| Restore a specific backup                | `python3 /path/to/scripts/restore.py --name stable-config`              |
| List all available versions              | `python3 /path/to/scripts/restore.py --list`                             |

---

## Troubleshooting

**"Error: .env file not found"**
→ You haven't created the `.env` file yet. Run `cp .env.example .env` and fill in your values.

**"Error: Missing values in .env file"**
→ `BACKUP_PASSWORD` must always be set. `GITHUB_PAT` and `GITHUB_USERNAME` must be set too, unless the GitHub CLI is installed and logged in (`gh auth login`).

**"Error: gpg not found. Install with: ..."**
→ GPG is not installed on this workspace. Run the install command (or `setup.py`) and try again.

**"Clone failed" during restore**
→ Your token or username is wrong, or the repo doesn't exist. Check the `GitHub auth:` line the script prints, make sure the token hasn't expired, and verify you have access to the private repo on GitHub.

**"Decryption failed — wrong password?"**
→ The `BACKUP_PASSWORD` in your `.env` doesn't match the one used when the backup was created. Check that it's spelled correctly and hasn't been changed.

**"Error: checksum mismatch!"**
→ The backup file is corrupted (checksum verification failed). This can happen if:
- The file was partially downloaded
- The GitHub transfer was interrupted
- A disk I/O error happened during restore

Try running restore again. If it keeps happening, try restoring a different backup version.

**"No backups found in repo"**
→ You haven't taken any backups yet, or you're pointing at the wrong repo. Make sure:
- `REPO_NAME` in `.env` is correct (default `xo-workspace-backup`)
- You've run `backup.py` at least once on some workspace

**"Note: skipped N backup(s) in an unsupported older format"**
→ Those backups were made by an older, incompatible version of this tool and can't be restored with it.

**"Error: backup creation failed"**
→ The `tar:` or `gpg:` line below it says why. Most often GPG isn't installed. Run `setup.py` and try again.

**"Error: `git commit` failed" during backup**
→ The `git:` line below it has the reason. If it says "Author identity unknown", set your git identity once:
```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

**"Error: Transport repo not initialized."**
→ Run `setup.py` first to initialize the backup repo.

**"Push failed" during backup**
→ Check your internet connection. Make sure your token:
- Has the `repo` scope (or Contents: Read and write, for fine-grained tokens)
- Hasn't expired
- Is spelled correctly in `.env`

**"I see fewer backups than expected"**
→ Only the 10 most recent backups are kept. If you had more than 10, the oldest ones were cleaned up. To keep more, edit `MAX_VERSIONS` in `backup.py`.

**"How do I verify my backup is working?"**
→ Run `backup.py` to create a backup, then run `restore.py --list` to see if it appears in the list.

---

## Important Notes

- **All your keys live in `.env`.** It's the only file you need to keep safe. Don't share it or commit it to a public repo.
- **Backups are encrypted with AES-256.** Without your password, nobody can read their contents.
- **Each backup is a full snapshot**, not just the changes, so large folders produce large backups.
- **Restore does not delete existing files, but it does overwrite them.** Files from the backup are added or overwritten, and anything not in the backup stays untouched.
- **Your Claude Code login is never backed up.** Log in again after restoring on a new machine.
- **Run setup.py on every new workspace.** It installs GPG and syncs backups from GitHub.
- **The system keeps 10 backups by default** and deletes older ones. Edit `MAX_VERSIONS` in `backup.py` if you want to keep more.
- **Large backups are automatically chunked** into 95 MB pieces for GitHub compatibility. Restore reassembles them automatically.

---

## Support & Feedback

For issues, feature requests, or contributions: [GitHub Issues](https://github.com/KrishBhimani/workspace-snapshot/issues)

Last updated: September 29, 2026

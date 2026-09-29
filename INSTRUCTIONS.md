# OpenClaw Snapshot — Backup & Restore Guide

Complete guide to backing up and restoring your OpenClaw agent. No advanced tech knowledge required — just follow the steps in order.

---

## What Do These Scripts Do?

- **backup.py** — Takes a snapshot of your OpenClaw agent (the `.openclaw` folder, plus any other folders you list in `SNAPSHOT_FOLDERS`), compresses it, encrypts it with a password, and uploads it to a private GitHub repository. Large backups are automatically split into 95 MB chunks for GitHub compatibility. Each backup is saved in its own folder — named `openclaw-<timestamp>` by default, or a custom name if you pass `--name` — and the system keeps the 10 most recent backups automatically.

- **restore.py** — Downloads your backups from GitHub, lets you pick which version you want (or use command-line flags for automation), reassembles chunks if needed, verifies the backup integrity, decrypts it, and restores your folders to their original locations. Your agent is back, exactly how it was.

- **setup.py** — Sets up dependencies, installs GPG encryption tools, and connects to your GitHub repo. Safe to run multiple times — it will sync the latest backups from GitHub without deleting anything.

Think of it like saving and loading a game — **backup** saves your progress, **restore** loads it on any machine.

---

## Folder Structure

Everything lives in one folder:

```
openclaw-snapshot/
├── .env.example        ← template (shows what keys you need)
├── .env                ← your actual keys (you create this)
├── scripts/
│   ├── config.py       ← shared config loader (don't edit)
│   ├── setup.py        ← run to set things up / sync backups
│   ├── backup.py       ← run to take a backup
│   └── restore.py      ← run to restore a version
├── SKILL.md            ← developer/integration docs
└── instructions.md     ← this file
```

All your keys (password, GitHub token) live in the `.env` file — one place, easy to manage.

---

## Before You Start (One-Time Setup)

### Step 1 — Install GPG (encryption tool)

Run this in your terminal:

```bash
sudo apt-get update && sudo apt-get install -y gnupg gpg-agent
```

This installs the tool that encrypts and decrypts your backups. You need to run this on **every new workspace** before using backup or restore.

### Step 2 — Create a GitHub repo

1. Go to [github.com/new](https://github.com/new)
2. Name it `openclaw-transport`
3. Set it to **Private**
4. Click **Create repository**

### Step 3 — Create a GitHub PAT token

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Click **"Generate new token (fine-grained)"**
3. Give it a name like `openclaw-backup`
4. Select the **`repo`** scope (full control of private repositories)
5. Click **Generate token**
6. **Copy the token immediately** — GitHub will only show it once

### Step 4 — Fill in your .env file

Navigate to the openclaw-snapshot folder:

```bash
cd /path/to/openclaw-snapshot
cp .env.example .env
```

Now open `.env` in any editor and fill in your values:

```
BACKUP_PASSWORD=your-strong-password-here
GITHUB_PAT=ghp_xxxxxxxxxxxxxxxxxxxx
GITHUB_USERNAME=YourGitHubUsername
REPO_NAME=openclaw-transport
```

**Optional — back up more than just `.openclaw`.** Add a `SNAPSHOT_FOLDERS` line
with a comma-separated list of folders relative to your home directory (e.g.
`/home/coder`). Leave it out to back up only `.openclaw`:

```
SNAPSHOT_FOLDERS=.openclaw, projects, notes
```

Each entry can be a direct child of home or a nested path like `work/configs`.

**Choose a strong backup password and remember it** — you'll need it if you ever restore on a machine that doesn't have this `.env` file.

### Step 5 — Run setup

```bash
python3 /path/to/openclaw-snapshot/scripts/setup.py
```

You'll see:

```
==================================================
  OpenClaw Snapshot — Setup
==================================================

✓ Config loaded from .env
  GitHub user: YourUsername
  Repo: openclaw-transport

[1/2] Checking GPG...
✓ GPG already installed

[2/2] Setting up GitHub transport repo...
✓ Repo cloned (existing backups preserved)

==================================================
  Setup complete!
==================================================

  To backup:   python3 /path/to/openclaw-snapshot/scripts/backup.py
  To restore:  python3 /path/to/openclaw-snapshot/scripts/restore.py
```

Done. You're ready to backup and restore.

---

## How to Take a Backup

Make sure GPG is installed first (if on a new workspace):

```bash
sudo apt-get update && sudo apt-get install -y gnupg gpg-agent
```

Then run:

```bash
python3 /path/to/openclaw-snapshot/scripts/backup.py
```

To give the backup folder a custom name in GitHub (instead of the default
`openclaw-<timestamp>`), add `--name`:

```bash
python3 /path/to/openclaw-snapshot/scripts/backup.py --name stable-config
```

The name may use letters, digits, `.`, `-` and `_` (no spaces or slashes). If you
reuse a name, the new backup cleanly replaces the old folder of that name.

**What happens:**

1. It syncs the latest from GitHub (so existing backups from other workspaces are preserved)
2. The folders in `SNAPSHOT_FOLDERS` (default just `.openclaw`) get compressed and encrypted
3. If the backup is larger than 95 MB, it's automatically split into chunks (see "Understanding Backup Chunks" below)
4. A `manifest.json` file is created with metadata (name, timestamp, folders, size, checksums, chunk info)
5. Everything gets pushed to your private GitHub repo

You'll see:

```
Folders to snapshot: .openclaw, projects
Syncing with GitHub...
Creating backup: stable-config
Backup created: stable-config (1542.3 MB, 3 part(s))
Pushed to GitHub
Backup complete: stable-config
```

**Tip:** Run this before making big changes to your agent, or at the end of each day.

---

## Understanding Backup Chunks

**Why chunks?** GitHub has file size limits. If your `.openclaw` folder is large, the backup is automatically split into 95 MB pieces.

**What it looks like on GitHub:**

```
openclaw-transport/backups/
└── openclaw-20260227-120000/          ← Backup folder (or your custom --name)
    ├── manifest.json                  ← Metadata (name, timestamp, folders, size, checksum, etc.)
    ├── part-000.gpg                   ← Chunk 1 (95 MB)
    ├── part-001.gpg                   ← Chunk 2 (95 MB)
    └── part-002.gpg                   ← Chunk 3 (remainder)
```

For smaller backups (under 95 MB), you'll see just one chunk:

```
openclaw-transport/backups/
└── openclaw-20260227-120000/
    ├── manifest.json
    └── part-000.gpg                   ← Single file (not split)
```

**The good news:** You don't need to think about this. When you restore, the scripts automatically reassemble chunks, verify checksums, and decrypt everything. It's all transparent.

---

## How to Restore

Make sure GPG is installed first (if on a new workspace):

```bash
sudo apt-get update && sudo apt-get install -y gnupg gpg-agent
```

### Basic restore (interactive mode)

```bash
python3 /path/to/openclaw-snapshot/scripts/restore.py
```

You'll see a list of all saved versions:

```
Cloning backup repo...

Available versions (4):
------------------------------------------------------------
  [1] stable-config  (1542.3 MB, 3 part(s)) ← latest
        created: 20260227-120000
        folders: .openclaw, projects
  [2] openclaw-20260226-090000  (1510.1 MB, single file)
        folders: .openclaw
  [3] openclaw-20260225-150000  (1498.7 MB, 2 part(s))
        folders: .openclaw
  [4] openclaw-20260225-103000  (1480.2 MB, single file)
        folders: .openclaw
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

Restored .openclaw, projects into /home/coder (from stable-config)
```

### Advanced restore modes

Use command-line flags for automation and scripting:

**Restore the latest backup (non-interactive):**
```bash
python3 /path/to/openclaw-snapshot/scripts/restore.py --latest
```

**Restore a specific backup by its name (or timestamp):**
```bash
python3 /path/to/openclaw-snapshot/scripts/restore.py --name stable-config
python3 /path/to/openclaw-snapshot/scripts/restore.py --name openclaw-20260226-090000
```
(`--version` still works as an alias and also matches a timestamp.)

**List all available backups and exit:**
```bash
python3 /path/to/openclaw-snapshot/scripts/restore.py --list
```

---

## Setting Up on a New Workspace (Quick Checklist)

When you move to a fresh workspace, here's everything you need to do in order:

1. Copy the `openclaw-snapshot` folder to the new workspace (or clone it from a safe location)
2. Create or update your `.env` file with your credentials
3. Install GPG:
   ```bash
   sudo apt-get update && sudo apt-get install -y gnupg gpg-agent
   ```
4. Run setup to sync backups from GitHub:
   ```bash
   python3 /path/to/openclaw-snapshot/scripts/setup.py
   ```
5. Restore your agent:
   ```bash
   python3 /path/to/openclaw-snapshot/scripts/restore.py --latest
   ```
6. Restart OpenClaw (if needed):
   ```bash
   openclaw gateway restart
   ```

That's it — your agent is running on the new workspace.

---

## Syncing Backups from Other Workspaces

If you backed up from a different workspace and your local `openclaw-transport` folder doesn't have the latest backups, just run setup again:

```bash
python3 /path/to/openclaw-snapshot/scripts/setup.py
```

This is safe to run anytime — it pulls the latest backups from GitHub without deleting anything. After syncing, you can run `backup.py` or `restore.py` as normal.

---

## Automatic Backup Cleanup

The system **keeps the 10 most recent backups** and automatically removes older ones to manage GitHub storage.

For example, if you have 15 backups:
- Backups 1–10 (newest) are kept
- Backups 11–15 (oldest) are deleted

This happens during `backup.py` — you'll see:

```
Removing old backup: openclaw-20260220-050000
Backup created: openclaw-20260227-120000 (1542.3 MB, 3 part(s))
```

**If you want to keep more backups,** you can edit `backup.py` line 21:
```python
MAX_VERSIONS = 10  # Change to a higher number like 20 or 50
```

---

## Where Are My Backups Stored?

On GitHub, your `openclaw-transport` repo's backup folder structure looks like this:

```
openclaw-transport/
└── backups/
    ├── openclaw-20260225-103000/
    │   ├── manifest.json
    │   └── part-000.gpg
    ├── openclaw-20260225-150000/
    │   ├── manifest.json
    │   ├── part-000.gpg
    │   └── part-001.gpg
    ├── openclaw-20260226-090000/
    │   ├── manifest.json
    │   └── part-000.gpg
    └── openclaw-20260227-120000/
        ├── manifest.json
        ├── part-000.gpg
        ├── part-001.gpg
        └── part-002.gpg
```

**Key points:**
- Each backup is a **folder** (not a single file). Its name is `openclaw-<timestamp>` by default, or whatever you passed to `--name`
- The `manifest.json` file contains metadata: backup name, timestamp, the folders included, checksum, chunk count, total size, etc.
- `part-*.gpg` files are the encrypted chunks (each ~95 MB, or smaller for the last chunk)
- The default timestamp in the folder name is in UTC format (YYYYMMDD-HHMMSS)

**All backups are encrypted.** Without your `BACKUP_PASSWORD`, nobody can read them — not even someone with access to your GitHub repo.

---

## What Gets Backed Up? What Doesn't?

**Included:**
- All of `.openclaw/` except the items listed below
- Any additional folders you set in `SNAPSHOT_FOLDERS` (each backed up in full, minus the exclusions below)
- Agent configuration, integrations, models, tools
- Gmail, Google Calendar, Slack, Stripe, Vercel connector data
- Local credentials (in `.openclaw/credentials/`)
- WhatsApp store data (except the session files listed below)

**Excluded (for security and workspace-specific reasons):**
- `.env` files (they contain secrets)
- `.git` folders
- `node_modules/` directories
- WhatsApp session files (`whatsapp/store/sessions-*`)
- WhatsApp credentials folder (`credentials/whatsapp/`)
- Unix socket files (`*.sock`)

**⚠️ Important:** WhatsApp sessions and credentials are workspace-specific and not included in backups. After restoring on a new machine, you'll need to reconnect WhatsApp using Baileys.

---

## Quick Reference

| I want to...                             | Run this                                                                   |
|------------------------------------------|---------------------------------------------------------------------------|
| Install GPG (every new workspace)        | `sudo apt-get update && sudo apt-get install -y gnupg gpg-agent`         |
| First-time setup / sync backups          | `python3 /path/to/scripts/setup.py`                                      |
| Take a backup                            | `python3 /path/to/scripts/backup.py`                                     |
| Take a backup with a custom name         | `python3 /path/to/scripts/backup.py --name stable-config`               |
| Restore a version (interactive)          | `python3 /path/to/scripts/restore.py`                                    |
| Restore latest (non-interactive)         | `python3 /path/to/scripts/restore.py --latest`                           |
| Restore a specific backup                | `python3 /path/to/scripts/restore.py --name stable-config`              |
| List all available versions              | `python3 /path/to/scripts/restore.py --list`                             |
| Restart OpenClaw after restore           | `openclaw gateway restart`                                                |

---

## Troubleshooting

**"Error: .env file not found"**
→ You haven't created the `.env` file yet. Run `cp .env.example .env` and fill in your values.

**"Error: Missing values in .env file"**
→ Open your `.env` file and make sure `BACKUP_PASSWORD`, `GITHUB_PAT`, and `GITHUB_USERNAME` all have values.

**"Error: GPG not found. Install with: sudo apt-get update && sudo apt-get install -y gnupg gpg-agent"**
→ GPG is not installed on this workspace. Run the install command and try again. You need to do this on every new workspace.

**"Clone failed" during restore**
→ Your PAT token or username is wrong. Double-check both in `.env`. Make sure the token hasn't expired. Verify that you have access to the private repo on GitHub.

**"Decryption failed — wrong password?"**
→ The `BACKUP_PASSWORD` in your `.env` doesn't match the one used when the backup was created. Check that it's spelled correctly and hasn't been changed.

**"Error: checksum mismatch!"**
→ The backup file is corrupted (checksum verification failed). This can happen if:
- The file was partially downloaded
- GitHub transfer was interrupted
- Disk I/O error during restore

Try running restore again. If it persists, try restoring a different backup version.

**"No backups found in repo"**
→ You haven't taken any backups yet, or you're pointing to the wrong repo. Make sure:
- Your `REPO_URL` in the config is correct
- You've run `backup.py` at least once on some workspace
- The GitHub repo is not empty

**"Error: backup creation failed"**
→ GPG is probably not installed. Run `sudo apt-get update && sudo apt-get install -y gnupg gpg-agent` and try again.

**"Error: Transport repo not initialized."**
→ Run `setup.py` first to initialize the backup repo. This clones or creates the GitHub transport repo.

**"Push failed during backup"**
→ Check your internet connection. Make sure your PAT token:
- Has the `repo` scope
- Hasn't expired
- Is spelled correctly in `.env`

**"Backup deleted old versions from GitHub (I see fewer backups than expected)"**
→ The system automatically keeps only the 10 most recent backups. If you had more than 10, the oldest ones were cleaned up. This is normal and saves GitHub storage. If you need to keep more, edit `backup.py` line 21 (`MAX_VERSIONS`).

**"How do I verify my backup is working?"**
→ Run `backup.py` to create a backup, then run `restore.py --list` to see if it appears in the list. The checksum should be shown in the manifest.json file stored on GitHub.

---

## Important Notes

- **All your keys live in `.env`.** This is the only file you need to keep safe. Don't share it or commit it to a public repo.
- **Backups are encrypted with AES-256.** Without your password, nobody can read them — not even someone with access to your GitHub repo.
- **Each backup is a full snapshot**, not just the changes. Large agents can result in large backups.
- **Restore does not delete existing files.** It extracts your backed-up folders back into place — files from the backup get added or overwritten, but anything not in the backup stays untouched. (New backups restore each folder to its original spot under home; older `.openclaw`-only backups restore into `~/.openclaw`.)
- **WhatsApp sessions and credentials are not included** in backups (they're workspace-specific). You'll need to reconnect WhatsApp after restoring on a new machine.
- **Install GPG on every new workspace** before running backup or restore.
- **Run setup.py to sync** if you've backed up from another workspace and need those backups available locally.
- **The system keeps 10 backups by default** and auto-deletes older ones. Edit `MAX_VERSIONS` in `backup.py` if you want to keep more.
- **Large backups are automatically chunked** into 95 MB pieces for GitHub compatibility. This is transparent — restore handles reassembly automatically.

---

## Backwards Compatibility

If you have **legacy backups** from older versions of this tool (single `.tgz.gpg` files instead of the newer folder format), the restore script still supports them. Legacy backups will appear in the version list and can be restored normally. No action needed — the system handles both formats automatically.

Older folder-format backups that contained only `.openclaw` are also fully supported: the restore script detects their layout from the manifest and extracts them back into `~/.openclaw`, while newer backups (which may contain several folders) are restored to their original locations under your home directory. Both old `openclaw-<timestamp>` names and new custom names are listed and selectable side by side.

---

## Support & Feedback

For issues, feature requests, or contributions: [GitHub Issues](https://github.com/KrishBhimani/openclaw-snapshot/issues)

Last updated: June 16, 2026

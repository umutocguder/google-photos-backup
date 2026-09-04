# Google Photos Backup

A high-performance, incremental, and deduplicating backup engine for Google Photos with EXIF timestamp preservation, dual-mode operation (Rich CLI & local FastAPI Web Dashboard), and Google Takeout reconciliation.

---

## 🌟 Key Features

- **Full Original Resolution**: Downloads images and videos in full quality (`=d` and `=dv` flags).
- **Incremental Synchronization**: Checks local SQLite database (`storage/metadata.db`) before fetching; skips previously synchronized media.
- **SHA-256 Deduplication**: Detects identical files across different albums or date ranges without wasting local disk space.
- **Timestamp & EXIF Preservation**: Preserves original photo capture time directly onto file system modification and access dates (`mtime`/`atime`).
- **Flexible Directory Layouts**:
  - By Date: `downloads/YYYY/MM/<filename>`
  - By Album: `downloads/Albums/<Album_Name>/<filename>`
- **Google Takeout Reconciliation**: Imports existing Takeout folders/ZIPs, parses companion `.json` sidecars, and indexes them into the backup library.
- **Dual Interface**:
  - Command Line: Fast, interactive terminal controls.
  - Web Dashboard: Modern local web management interface with real-time sync progress, media counts, and storage metrics.

---

## 🚀 Quick Start

### 1. Installation

Clone or open the project and install requirements:

```bash
cd /Users/umut/mycodespaces/google-photos-backup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Google Cloud OAuth Setup

To access your personal Google Photos library, you need an OAuth 2.0 Client ID:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project named `Google Photos Backup` (or select an existing project).
3. Enable the **Google Photos Library API** under **APIs & Services > Library**.
4. Configure the **OAuth Consent Screen**:
   - User Type: **External**
   - Add your Gmail address under **Test Users**.
5. Under **APIs & Services > Credentials**:
   - Click **Create Credentials > OAuth client ID**.
   - Select **Desktop App**.
   - Download the client configuration JSON, rename it to `credentials.json`, and place it in the root of this project:
     `/Users/umut/mycodespaces/google-photos-backup/credentials.json`

### 3. Authentication

Run the authentication flow:

```bash
python3 main.py auth
```
This opens your browser for one-click authorization and writes `token.json` locally.

---

## 💻 CLI Usage

### Incremental Synchronization
```bash
# Start incremental backup with default settings (by date, 5 concurrent workers)
python3 main.py sync

# Backup organized by albums
python3 main.py sync --organize album

# Limit sync to 50 items for testing
python3 main.py sync --limit 50 --workers 10
```

### View Status & Storage Metrics
```bash
python3 main.py status
```

### List Albums
```bash
python3 main.py albums
```

### Import Google Takeout Archive
```bash
python3 main.py takeout /path/to/GoogleTakeout/GooglePhotos
```

### Launch Web Dashboard
```bash
python3 main.py web --port 8080
```
Open [http://127.0.0.1:8080](http://127.0.0.1:8080) to monitor backups, view storage statistics, and trigger background syncs.

---

## 📂 Project Structure

```text
google-photos-backup/
├── AGENTS.md                  # Project standards & guidelines
├── CLAUDE.md                  # Claude Code integration
├── WORKLOG.md                 # AI handoff changelog
├── README.md                  # Documentation
├── .gitignore                 # Secrets & ignore list
├── requirements.txt           # Python dependencies
├── pyproject.toml             # Packaging configuration
│
├── src/
│   ├── config.py              # Path and runtime configuration
│   ├── auth.py                # OAuth 2.0 flow & token refresh
│   ├── client.py              # Google Photos Library API client
│   ├── database.py            # SQLite metadata tracking & deduplication
│   ├── downloader.py          # Concurrent resumable media downloader
│   ├── takeout.py             # Takeout sidecar parser & importer
│   ├── cli.py                 # Rich command-line interface
│   │
│   └── web/                   # Local FastAPI dashboard
│       ├── app.py             # Server endpoints & background tasks
│       └── templates/         # HTML template
│
└── main.py                    # Unified entrypoint
```

---

## 🔒 Security & Privacy

- **Never Commit Secrets**: `credentials.json` and `token.json` are strictly ignored by `.gitignore`.
- **Local Storage**: All metadata and media are stored locally on your machine.

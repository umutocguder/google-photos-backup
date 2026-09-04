# AGENTS.md — Google Photos Backup Project Guidelines

This document defines the architectural rules, coding standards, and operational guidelines for the **Google Photos Backup** project (`google-photos-backup`). All AI agents (Antigravity, Claude, Cursor) and human contributors must strictly follow these instructions.

---

## 1. Project Overview & Architecture

`google-photos-backup` is a high-performance, incremental, deduplicating backup engine for Google Photos with both a rich CLI and a local FastAPI management web dashboard.

### Core Capabilities
1. **OAuth 2.0 Flow**: Secure user consent with Google Photos Library API scope, token refresh, and credential caching (`token.json`).
2. **Incremental & Deduplicating Sync Engine**:
   - Downloads original quality media (`=d` direct download parameter).
   - Tracks media IDs, file size, MIME types, creation timestamps, and SHA-256 checksums in local SQLite (`storage/metadata.db`).
   - Skips already downloaded or identical files.
3. **Metadata & Timestamp Preservation**:
   - Updates filesystem timestamps (`st_mtime`, `st_atime`) to match the original Google Photos capture time.
   - Preserves EXIF metadata.
4. **Flexible Organization**:
   - Date-based hierarchical tree (`YYYY/MM/` or `YYYY/YYYY-MM-DD/`).
   - Album-based mirror (`Albums/<Album_Name>/`).
5. **Google Takeout Support**:
   - Imports and reconciles Google Takeout ZIP/directory exports with JSON sidecars (`metadata.json`).
6. **Dual-Mode UI**:
   - Modern CLI with Rich terminal output (`sync`, `auth`, `status`, `albums`, `takeout`).
   - Local FastAPI web dashboard with live sync progress, storage analytics, and media catalog.

---

## 2. Mandatory Coding Standards (STRICT ENGLISH RULE)

1. **Source Code**:
   - Variable names, functions, classes, methods, dataclasses/models, type hints, and comments **MUST ALWAYS BE IN ENGLISH**.
2. **Commit Messages**:
   - All git commit messages must be in English following the Conventional Commits specification (`feat: ...`, `fix: ...`, `chore: ...`, `refactor: ...`).
3. **UI Text**:
   - The CLI and Web dashboard may offer Turkish or bilingual text for the end-user, but the underlying codebase must remain 100% English.

---

## 3. Tech Stack & Directory Structure

- **Runtime**: Python 3.12+
- **API & HTTP**: `google-auth`, `google-auth-oauthlib`, `aiohttp`, `requests`
- **Database**: SQLite3 (Standard library `sqlite3` + `storage/metadata.db`)
- **CLI Framework**: Standard `argparse` / `rich` for rich progress bars and tables
- **Web UI**: `fastapi`, `uvicorn`, `jinja2`, Tailwind CSS (CDN)

```text
google-photos-backup/
├── AGENTS.md                  # Project rules & architecture
├── CLAUDE.md                  # Claude Code entrypoint (@AGENTS.md)
├── WORKLOG.md                 # AI handoff changelog
├── README.md                  # Setup & usage documentation
├── .gitignore                 # Secrets & ignore list
├── requirements.txt           # Python dependencies
├── pyproject.toml             # Project metadata
│
├── src/
│   ├── __init__.py
│   ├── config.py              # App configuration & environment loader
│   ├── auth.py                # Google OAuth 2.0 flow & token management
│   ├── client.py              # Google Photos Library API client
│   ├── database.py            # SQLite storage & deduplication engine
│   ├── downloader.py          # Concurrent, resumable media downloader
│   ├── takeout.py             # Google Takeout archive & sidecar parser
│   ├── cli.py                 # Rich interactive terminal interface
│   │
│   └── web/                   # Local management dashboard
│       ├── app.py             # FastAPI backend
│       ├── static/            # Static assets
│       └── templates/         # Dashboard HTML template
│
└── main.py                    # Unified entry point (CLI & Web)
```

---

## 4. Security & Privacy Rules

- **Secrets Isolation**: `credentials.json`, `client_secret*.json`, and `token.json` must **NEVER** be committed to Git.
- **Data Protection**: Personal photos, downloaded videos, and local database files are strictly ignored by `.gitignore`.
- **Git Author**: All commits must use the identity `Umut Öçgüder <umutocgdr@gmail.com>`.
- **Repository Scope**: This is a personal repository. It must remain in a **Private** GitHub repository (`umutocguder/google-photos-backup`).
